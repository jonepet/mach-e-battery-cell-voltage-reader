import asyncio
import contextlib
import glob
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from mache_cells.cells import CellBlockError, read_cell_voltages
from mache_cells.config import Settings
from mache_cells.elm327 import AdapterError, AdapterInfo, Elm327
from mache_cells.signals import SignalReading, read_signals
from mache_cells.stats import CellStats, analyse
from mache_cells.transport import SerialTransport, Transport, TransportError
from mache_cells.uds import UdsClient, UdsError

TransportFactory = Callable[[str, int], Transport]


class RequestError(Exception):
    pass


@dataclass(frozen=True)
class Reading:
    timestamp: float
    duration_s: float
    voltages: list[float | None]
    stats: CellStats | None
    cell_error: str | None
    signals: list[SignalReading]


@dataclass
class State:
    status: str = "disconnected"
    port: str | None = None
    adapter: AdapterInfo | None = None
    error: str | None = None
    reading: Reading | None = None

    def public(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "port": self.port,
            "adapter": None if self.adapter is None else asdict(self.adapter),
            "error": self.error,
            "reading": None if self.reading is None else asdict(self.reading),
        }


class CellMonitor:
    """Owns the adapter connection and reads the cell block and battery signals in a loop."""

    def __init__(self, settings: Settings, open_transport: TransportFactory = SerialTransport) -> None:
        self._settings = settings
        self._open_transport = open_transport
        self._state = State()
        self._adapter: Elm327 | None = None
        self._task: asyncio.Task[None] | None = None
        self._lifecycle = asyncio.Lock()

    @property
    def state(self) -> dict[str, Any]:
        return self._state.public()

    def available_ports(self) -> list[str]:
        return sorted({path for pattern in self._settings.port_patterns for path in glob.glob(pattern)})

    async def connect(self, port: str) -> None:
        if port not in self.available_ports():
            raise RequestError(f"unknown port {port!r}")
        async with self._lifecycle:
            await self._disconnect()
            self._state = State(status="connecting", port=port)
            try:
                adapter, info = await asyncio.to_thread(self._open_adapter, port)
            except (TransportError, AdapterError) as exc:
                self._state.status, self._state.error = "failed", str(exc)
                return
            self._adapter = adapter
            self._state.status, self._state.adapter = "connected", info
            self._task = asyncio.create_task(self._read_loop(adapter))

    async def disconnect(self) -> None:
        async with self._lifecycle:
            await self._disconnect()
            self._state.status = "disconnected"

    async def _disconnect(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        self._task = None
        adapter, self._adapter = self._adapter, None
        if adapter is not None:
            await self._close(adapter)

    def _open_adapter(self, port: str) -> tuple[Elm327, AdapterInfo]:
        settings = self._settings
        adapter = Elm327(
            self._open_transport(port, settings.baudrate),
            settings.command_timeout_s,
            settings.reset_timeout_s,
            settings.separation_ms,
            settings.frame_timeout_ms,
        )
        try:
            return adapter, adapter.initialize()
        except (TransportError, AdapterError):
            adapter.close()
            raise

    async def _read_loop(self, adapter: Elm327) -> None:
        uds = UdsClient(adapter)
        while True:
            started = time.monotonic()
            try:
                reading = await _bus_call(self._read, uds)
            except TransportError as exc:
                await self._fail(str(exc))
                return
            self._state.reading = reading
            await asyncio.sleep(max(0.0, self._settings.read_interval_s - (time.monotonic() - started)))

    def _read(self, uds: UdsClient) -> Reading:
        started = time.monotonic()
        voltages: list[float | None] = []
        cell_error = None
        try:
            voltages = read_cell_voltages(uds)
        except (AdapterError, UdsError, CellBlockError) as exc:
            cell_error = str(exc)
        signals = read_signals(uds)
        stats = analyse(voltages, self._settings.outlier_deviation_v, self._settings.spread_warning_v)
        return Reading(time.time(), time.monotonic() - started, voltages, stats, cell_error, signals)

    async def _fail(self, error: str) -> None:
        adapter, self._adapter = self._adapter, None
        self._task = None
        self._state.status, self._state.error = "failed", error
        if adapter is not None:
            await self._close(adapter)

    async def _close(self, adapter: Elm327) -> None:
        """Release the port without letting a vanished device hold the service.

        Closing a serial port whose USB device disappeared without a disconnect event can block in the
        kernel until the USB stack gives up, so the wait is bounded and the close finishes on its own.
        """
        limit = self._settings.reset_timeout_s
        try:
            await asyncio.wait_for(asyncio.to_thread(adapter.close), limit)
        except TimeoutError:
            self._state.error = f"adapter port did not close within {limit:.0f}s; device not responding"


async def _bus_call[T](function: Callable[..., T], *args: object) -> T:
    """Run blocking adapter I/O in a worker thread without letting it outlive a cancelled task.

    A cancelled read must not keep talking to the adapter after the port is handed to a new connection.
    """
    call = asyncio.ensure_future(asyncio.to_thread(function, *args))
    try:
        return await asyncio.shield(call)
    except asyncio.CancelledError:
        await asyncio.wait([call])
        raise
