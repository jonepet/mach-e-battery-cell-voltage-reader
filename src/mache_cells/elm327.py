import math
import threading
from dataclasses import dataclass

from mache_cells.isotp import IsoTpError, parse_frame, reassemble
from mache_cells.transport import ReplyLost, Transport


class AdapterError(Exception):
    pass


class NoResponse(AdapterError):
    """No module answered within the adapter timeout."""


class CorruptReply(AdapterError):
    """A reply arrived but its frames could not be parsed or reassembled, e.g. bytes lost on the link."""


@dataclass(frozen=True)
class AdapterInfo:
    elm_version: str | None
    device: str | None
    battery_voltage: str | None


def check_timing(separation_ms: int, frame_timeout_ms: int) -> None:
    """ISO-TP allows 0-127 ms separation; ATST counts 4 ms steps up to 0xFF and must outlast it."""
    if not 0 <= separation_ms <= 0x7F:
        raise ValueError(f"ISO-TP separation time must be 0-127 ms, got {separation_ms}")
    if not separation_ms < frame_timeout_ms <= 0xFF * 4:
        raise ValueError(
            f"frame timeout must exceed the {separation_ms} ms separation time and be at most "
            f"{0xFF * 4} ms, got {frame_timeout_ms}"
        )


class Elm327:
    """ELM327 command set over CAN 11-bit 500 kbit/s (protocol 6), as implemented by OBDLink STN adapters.

    The adapter processes one command at a time, so every exchange holds the instance lock.
    """

    def __init__(
        self,
        transport: Transport,
        command_timeout_s: float,
        reset_timeout_s: float,
        separation_ms: int,
        frame_timeout_ms: int,
    ) -> None:
        """`frame_timeout_ms` replaces the adapter's adaptive timing with a fixed wait for each frame.

        Adaptive timing learns from fast single-frame replies and then ends a paced multi-frame reply
        between two frames, so the rest of it arrives as the reply to the next request.
        """
        check_timing(separation_ms, frame_timeout_ms)
        self._transport = transport
        self._command_timeout_s = command_timeout_s
        self._reset_timeout_s = reset_timeout_s
        self._separation_ms = separation_ms
        self._frame_timeout_ms = frame_timeout_ms
        self._addressing: tuple[int, int] | None = None
        self._lock = threading.Lock()

    def initialize(self) -> AdapterInfo:
        with self._lock:
            self._exchange("ATZ", self._reset_timeout_s)
            timing = ("ATAT0", f"ATST{math.ceil(self._frame_timeout_ms / 4):02X}")
            for command in ("ATE0", "ATL0", "ATS0", "ATH1", "ATSP6", "ATCAF1", "ATAL", *timing):
                self._expect_ok(command)
            self._addressing = None
            return AdapterInfo(
                elm_version=self._single_line("ATI"),
                device=self._single_line("STI"),
                battery_voltage=self._single_line("ATRV"),
            )

    def request(self, tx_id: int, rx_id: int, payload: bytes) -> list[bytes]:
        with self._lock:
            self._address(tx_id, rx_id)
            lines = self._exchange(payload.hex().upper(), self._command_timeout_s)
        replies = [line for line in lines if line != "SEARCHING..."]
        failure = next((line for line in replies if _is_error_reply(line)), None)
        if failure is not None:
            error = NoResponse if failure.startswith("NO DATA") else AdapterError
            raise error(f"{payload.hex().upper()} to {tx_id:03X}: {failure}")
        try:
            return reassemble([parse_frame(line) for line in replies], rx_id)
        except IsoTpError as exc:
            raise CorruptReply(f"{payload.hex().upper()} to {tx_id:03X}: {exc}") from exc

    def close(self) -> None:
        with self._lock:
            self._transport.close()

    def _address(self, tx_id: int, rx_id: int) -> None:
        if self._addressing == (tx_id, rx_id):
            return
        self._addressing = None
        self._expect_ok(f"ATSH{tx_id:03X}")
        self._expect_ok(f"ATCRA{rx_id:03X}")
        self._expect_ok(f"ATFCSH{tx_id:03X}")
        self._expect_ok(f"ATFCSD3000{self._separation_ms:02X}")
        self._expect_ok("ATFCSM1")
        self._addressing = (tx_id, rx_id)

    def _exchange(self, command: str, timeout_s: float) -> list[str]:
        try:
            return self._transport.exchange(command, timeout_s)
        except ReplyLost as exc:
            self._addressing = None
            raise CorruptReply(f"{command}: {exc}") from exc

    def _expect_ok(self, command: str) -> None:
        lines = self._exchange(command, self._command_timeout_s)
        if "OK" not in lines:
            raise AdapterError(f"{command} rejected: {lines}")

    def _single_line(self, command: str) -> str | None:
        lines = self._exchange(command, self._command_timeout_s)
        if not lines or lines[0] == "?":
            return None
        return lines[0]


def _is_error_reply(line: str) -> bool:
    return line.startswith(
        (
            "NO DATA",
            "CAN ERROR",
            "UNABLE TO CONNECT",
            "BUS ERROR",
            "BUS BUSY",
            "BUFFER FULL",
            "DATA ERROR",
            "FB ERROR",
            "RX ERROR",
            "STOPPED",
            "ACT ALERT",
            "LV RESET",
            "?",
        )
    )
