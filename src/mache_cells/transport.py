import contextlib
import errno
import time
from collections.abc import Callable
from typing import Protocol

import serial


class TransportError(Exception):
    pass


class PortBusy(TransportError):
    """Another program holds the adapter port."""


class ReplyLost(Exception):
    """Part of a reply, including its prompt, never arrived, but the adapter answered a resync afterwards."""


class Transport(Protocol):
    def exchange(self, command: str, timeout_s: float) -> list[str]: ...

    def close(self) -> None: ...


def reply_lines(raw: bytes, command: str) -> list[str]:
    """Split adapter output (prompt removed) into non-empty lines, dropping the echo of the command.

    The ELM327 data sheet allows the adapter to emit NUL characters, which the host must ignore.
    """
    text = raw.replace(b"\x00", b"").decode("ascii", errors="replace").replace("\n", "\r")
    return [line.strip() for line in text.split("\r") if line.strip() and line.strip() != command]


def _held_by_another_program(exc: serial.SerialException) -> bool:
    """POSIX reports the failed exclusive lock with its errno. pyserial on Windows keeps no errno and only
    embeds the repr of WinError 5 (access denied), which a COM port gives while another program holds it."""
    return exc.errno in {errno.EWOULDBLOCK, errno.EAGAIN, errno.EBUSY} or "PermissionError(13," in str(exc)


class SerialTransport:
    """ELM327 command/reply exchange on a serial port, held exclusively: commands from a second program
    would interleave with ours and corrupt both programs' replies."""

    def __init__(self, port: str, baudrate: int) -> None:
        try:
            self._serial = serial.Serial(port=port, baudrate=baudrate, timeout=0.05, exclusive=True)
        except serial.SerialException as exc:
            error = PortBusy if _held_by_another_program(exc) else TransportError
            raise error(f"cannot open {port}: {exc}") from exc
        try:
            self._serial.reset_input_buffer()
        except (OSError, serial.SerialException) as exc:
            self.close()
            raise TransportError(f"cannot open {port}: {exc}") from exc

    def exchange(self, command: str, timeout_s: float) -> list[str]:
        try:
            self._serial.write(command.encode("ascii") + b"\r")
            raw = self._read_until_prompt(timeout_s)
        except serial.SerialException as exc:
            raise TransportError(f"adapter I/O failed during {command!r}: {exc}") from exc
        return reply_lines(raw, command)

    def close(self) -> None:
        """Release the port; a device that has already disappeared has nothing left to release."""
        with contextlib.suppress(OSError, serial.SerialException):
            self._serial.close()

    def _read_until_prompt(self, timeout_s: float) -> bytes:
        """Read until the prompt; the timeout counts silence, so a long multi-frame reply is never cut off.

        Silence after part of a reply means bytes were lost on the way, as happens when a USB relay stalls
        longer than the adapter's output buffer lasts; an adapter that still answers a resync is alive.
        """
        buffer = self._read_until(lambda received: received.endswith(b">"), timeout_s)
        if buffer is not None:
            return buffer[:-1]
        self._serial.write(b"ATI\r")
        if self._read_until(lambda received: b"ELM327" in received and received.endswith(b">"), timeout_s):
            raise ReplyLost("reply lost on the adapter link before its prompt; adapter resynchronised")
        raise TransportError(f"adapter silent for {timeout_s:.1f}s and did not answer a resync")

    def _read_until(self, done: Callable[[bytes], bool], silence_s: float) -> bytes | None:
        deadline = time.monotonic() + silence_s
        buffer = bytearray()
        while time.monotonic() < deadline:
            chunk = self._serial.read(self._serial.in_waiting or 1)
            if chunk:
                deadline = time.monotonic() + silence_s
            buffer += chunk
            if done(bytes(buffer)):
                return bytes(buffer)
        return None
