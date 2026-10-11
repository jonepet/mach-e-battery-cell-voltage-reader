import contextlib
import os
import pty
import threading
import time
from collections.abc import Callable, Iterator

import pytest
import serial

from mache_cells.transport import PortBusy, ReplyLost, SerialTransport, TransportError, reply_lines

Script = Callable[[int], None]


@pytest.fixture
def adapter_pty() -> Iterator[tuple[int, str]]:
    master, slave = pty.openpty()
    yield master, os.ttyname(slave)
    for descriptor in (master, slave):
        with contextlib.suppress(OSError):
            os.close(descriptor)


def read_command(master: int, command: bytes) -> None:
    received = b""
    while not received.endswith(command + b"\r"):
        received += os.read(master, 64)


def run(adapter_pty: tuple[int, str], script: Script, command: str, timeout_s: float) -> list[str]:
    master, port = adapter_pty
    responder = threading.Thread(target=script, args=(master,), daemon=True)
    responder.start()
    transport = SerialTransport(port, 115200)
    try:
        return transport.exchange(command, timeout_s)
    finally:
        transport.close()
        responder.join(timeout=2)


def test_nul_characters_from_the_adapter_are_ignored() -> None:
    raw = b"7EC1023624288034400\r\x007EC23FFFFFFFFFFFFFF\r"

    assert reply_lines(raw, "22D782") == ["7EC1023624288034400", "7EC23FFFFFFFFFFFFFF"]


def test_long_reply_that_keeps_arriving_is_not_cut_off(adapter_pty: tuple[int, str]) -> None:
    frames = [b"7EC1014622288034400\r", b"7EC2101000100010001\r", b"7EC2200000013001100\r"]

    def slow_module(master: int) -> None:
        read_command(master, b"224288")
        for frame in frames:
            time.sleep(0.2)
            os.write(master, frame)
        os.write(master, b"\r>")

    assert run(adapter_pty, slow_module, "224288", 0.3) == [frame.decode().strip() for frame in frames]


def test_lost_prompt_resynchronises(adapter_pty: tuple[int, str]) -> None:
    def relay_drops_the_tail(master: int) -> None:
        read_command(master, b"22FDF4")
        os.write(master, b"7EC146B62FDF44072B0\r")
        read_command(master, b"ATI")
        os.write(master, b"ELM327 v1.4b\r\r>")

    with pytest.raises(ReplyLost):
        run(adapter_pty, relay_drops_the_tail, "22FDF4", 0.3)


def test_silent_adapter_is_transport_error(adapter_pty: tuple[int, str]) -> None:
    with pytest.raises(TransportError, match=r"silent for 0\.3s"):
        run(adapter_pty, lambda master: None, "ATI", 0.3)


def test_port_in_use_by_another_reader_is_refused(adapter_pty: tuple[int, str]) -> None:
    _, port = adapter_pty
    first = SerialTransport(port, 115200)
    try:
        with pytest.raises(PortBusy, match="cannot open"):
            SerialTransport(port, 115200)
    finally:
        first.close()


def test_windows_port_held_by_another_program_is_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    def held(**_: object) -> None:
        raise serial.SerialException(
            "could not open port 'COM3': PermissionError(13, 'Ingen tilgang.', None, 5)"
        )

    monkeypatch.setattr(serial, "Serial", held)

    with pytest.raises(PortBusy):
        SerialTransport("COM3", 115200)


def test_unopenable_port_is_transport_error_but_not_busy() -> None:
    with pytest.raises(TransportError, match="cannot open") as raised:
        SerialTransport("/dev/does-not-exist", 115200)

    assert not isinstance(raised.value, PortBusy)
