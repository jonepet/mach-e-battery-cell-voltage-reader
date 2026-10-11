import asyncio
import contextlib
import fnmatch
import glob
import os
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import asdict, dataclass
from typing import Any

from serial.tools import list_ports

from mache_cells.balancing import Balancing, read_balancing
from mache_cells.cells import CellBlockError, TickWatch, read_cell_voltages
from mache_cells.config import Settings
from mache_cells.elm327 import AdapterError, AdapterInfo, Elm327
from mache_cells.health import GroupHealth, analyse_health, read_group_capacities
from mache_cells.signals import SignalReading, read_signals
from mache_cells.stats import CellStats, analyse
from mache_cells.transport import PortBusy, SerialTransport, Transport, TransportError
from mache_cells.uds import UdsClient, UdsError

TransportFactory = Callable[[str, int], Transport]


class RequestError(Exception):
    pass


@dataclass(frozen=True)
class Reading:
    timestamp: float
    duration_s: float
    voltages: list[float | None]
    voltages_age_s: float | None
    stats: CellStats | None
    cell_error: str | None
    health: GroupHealth | None
    health_error: str | None
    balancing: Balancing | None
    balancing_error: str | None
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
        self._changed = asyncio.Condition()
        self._version = 0

    @property
    def state(self) -> dict[str, Any]:
        return self._state.public()

    async def updates(self) -> AsyncIterator[dict[str, Any]]:
        """The current state, then the state after every change; changes between two yields coalesce."""
        seen = -1
        while True:
            async with self._changed:
                while self._version == seen:
                    await self._changed.wait()
                seen, state = self._version, self.state
            yield state

    async def _publish(self) -> None:
        async with self._changed:
            self._version += 1
            self._changed.notify_all()

    def available_ports(self) -> list[str]:
        """Ports matching the configured patterns: device files, and serial ports the operating system lists.

        Windows COM ports are not files, and a Bluetooth rfcomm binding is a file the port list may omit.
        Only absolute patterns name device files; a bare `COM*` would match files in the working directory.
        """
        patterns = self._settings.port_patterns
        files = {path for pattern in patterns if os.path.isabs(pattern) for path in glob.glob(pattern)}
        listed = {
            port.device
            for port in list_ports.comports()
            if any(fnmatch.fnmatch(port.device, pattern) for pattern in patterns)
        }
        return sorted(files | listed)

    async def connect(self, port: str) -> None:
        if port not in self.available_ports():
            raise RequestError(f"unknown port {port!r}")
        async with self._lifecycle:
            await self._disconnect()
            self._state = State(status="connecting", port=port)
            await self._publish()
            try:
                adapter, info = await asyncio.to_thread(self._open_adapter, port)
            except PortBusy as exc:
                self._state.status, self._state.error = "port_busy", str(exc)
                await self._publish()
                return
            except (TransportError, AdapterError) as exc:
                self._state.status, self._state.error = "failed", str(exc)
                await self._publish()
                return
            self._adapter = adapter
            self._state.status, self._state.adapter = "connected", info
            self._task = asyncio.create_task(self._read_loop(adapter))
            await self._publish()

    async def disconnect(self) -> None:
        async with self._lifecycle:
            await self._disconnect()
            self._state.status = "disconnected"
            await self._publish()

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
        tick_watch = TickWatch()
        while True:
            started = time.monotonic()
            try:
                reading = await _bus_call(self._read, uds, tick_watch)
            except TransportError as exc:
                await self._fail(str(exc))
                return
            self._state.reading = reading
            await self._publish()
            await asyncio.sleep(max(0.0, self._settings.read_interval_s - (time.monotonic() - started)))

    def _read(self, uds: UdsClient, tick_watch: TickWatch) -> Reading:
        started = time.monotonic()
        voltages: list[float | None] = []
        voltages_age_s = None
        cell_error = None
        try:
            cells = read_cell_voltages(uds)
            voltages, voltages_age_s = cells.voltages, tick_watch.age_s(cells.tick, time.monotonic())
        except (AdapterError, UdsError, CellBlockError) as exc:
            cell_error = str(exc)
        capacities: list[float | None] = []
        health_error = None
        try:
            capacities = read_group_capacities(uds, len(voltages) or None)
        except (AdapterError, UdsError, CellBlockError) as exc:
            health_error = str(exc)
        balancing = None
        balancing_error = None
        try:
            balancing = read_balancing(uds, len(voltages) or None)
        except (AdapterError, UdsError, CellBlockError) as exc:
            balancing_error = str(exc)
        signals = read_signals(uds)
        pack = {signal.key: signal.value for signal in signals}
        stats = analyse(voltages, self._settings.outlier_deviation_v, self._settings.spread_warning_v)
        health = analyse_health(capacities, pack["capacity"], pack["soh"])
        return Reading(
            time.time(),
            time.monotonic() - started,
            voltages,
            voltages_age_s,
            stats,
            cell_error,
            health,
            health_error,
            balancing,
            balancing_error,
            signals,
        )

    async def _fail(self, error: str) -> None:
        adapter, self._adapter = self._adapter, None
        self._task = None
        self._state.status, self._state.error = "failed", error
        if adapter is not None:
            await self._close(adapter)
        await self._publish()

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
