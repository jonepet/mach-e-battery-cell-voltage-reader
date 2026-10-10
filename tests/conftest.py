import struct

import pytest

from mache_cells.transport import reply_lines

LIVE_CELLS = [3.786 - 0.0001 * (cell % 9) for cell in range(94)]
CELL_BLOCK = (
    struct.pack(">94f", *LIVE_CELLS) + struct.pack(">94f", *[3.904] * 94) + struct.pack(">94f", *[3.840] * 94)
)
BECM_DATA = {
    0xFDF4: CELL_BLOCK,
    0xDD01: bytes.fromhex("03AFA2"),
    0x490C: bytes([0xB7]),
    0x485C: (2532).to_bytes(2, "big"),
    0x4801: (36637).to_bytes(2, "big"),
    0x4845: bytes([159]),
    0x4848: (30234).to_bytes(2, "big"),
    0x480D: (35627).to_bytes(2, "big"),
    0x4840: (3785).to_bytes(2, "big"),
    0x4841: (3790).to_bytes(2, "big"),
    0x4810: (13069).to_bytes(2, "big"),
    0x4800: bytes([53]),
    0x4808: bytes([56, 53, 3, 54]),
    0x4846: bytes([60]),
}


def segment(payload: bytes) -> list[bytes]:
    """Split a payload into ISO 15765-2 frames (8 data bytes each, unpadded tail)."""
    if len(payload) <= 7:
        return [bytes([len(payload)]) + payload]
    frames = [bytes([0x10 | (len(payload) >> 8), len(payload) & 0xFF]) + payload[:6]]
    rest = payload[6:]
    chunks = [rest[i : i + 7] for i in range(0, len(rest), 7)]
    return frames + [bytes([0x20 | ((index + 1) & 0x0F)]) + chunk for index, chunk in enumerate(chunks)]


class FakeAdapter:
    """Answers the ELM327 command set like an OBDLink on the car, with BECM data from a table."""

    def __init__(self, data: dict[int, bytes]) -> None:
        self.data = data
        self.sent: list[str] = []
        self.sent_after_close: list[str] = []
        self.closed = False
        self._tx_id: int | None = None

    def exchange(self, command: str, timeout_s: float) -> list[str]:
        (self.sent_after_close if self.closed else self.sent).append(command)
        raw = "\r".join(self._answer(command)).encode("ascii")
        return reply_lines(raw, command)

    def close(self) -> None:
        self.closed = True

    def _answer(self, command: str) -> list[str]:
        replies = {
            "ATZ": ["ELM327 v1.4b"],
            "ATI": ["ELM327 v1.4b"],
            "STI": ["STN2231 v5.10.3"],
            "ATRV": ["14.4V"],
        }
        if command.startswith("ATSH"):
            self._tx_id = int(command[4:], 16)
        if command.startswith(("AT", "ST")):
            return replies.get(command, ["OK"])
        if self._tx_id != 0x7E4:
            return ["NO DATA"]
        request = bytes.fromhex(command)
        payload = self.data.get(int.from_bytes(request[1:3], "big"))
        response = bytes([0x7F, 0x22, 0x31]) if payload is None else b"\x62" + request[1:3] + payload
        return [f"7EC{frame.hex().upper()}" for frame in segment(response)]


@pytest.fixture
def fake_adapter() -> FakeAdapter:
    return FakeAdapter(dict(BECM_DATA))
