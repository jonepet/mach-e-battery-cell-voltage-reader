import math
import struct
from dataclasses import dataclass

from mache_cells.uds import UdsClient

BECM_REQUEST_ID = 0x7E4
BECM_RESPONSE_ID = 0x7EC
CELL_VOLTAGE_DID = 0xFDE3
HEADER_BYTES = 16


class CellBlockError(Exception):
    pass


@dataclass(frozen=True)
class CellVoltages:
    """Live voltage of each series cell group, and the battery module's timestamp of the measurement."""

    voltages: list[float | None]
    tick: int


class TickWatch:
    """Seconds since the battery module's measurement timestamp last advanced on one connection."""

    def __init__(self) -> None:
        self._tick: int | None = None
        self._changed_at = 0.0

    def age_s(self, tick: int, now: float) -> float:
        if tick != self._tick:
            self._tick, self._changed_at = tick, now
        return now - self._changed_at


def decode_cell_voltages(data: bytes) -> CellVoltages:
    """A 16-byte header, then one big-endian IEEE 754 float per series cell group; NaN is returned as None.

    The first header word is the module's timestamp in 0.1 s ticks.
    """
    body = len(data) - HEADER_BYTES
    if body <= 0 or body % 4:
        raise CellBlockError(f"cell voltage block of {len(data)} bytes is not a header and 4-byte values")
    (tick,) = struct.unpack(">I", data[:4])
    return CellVoltages(decode_group_values(data[HEADER_BYTES:], None, "cell voltage"), tick)


def decode_group_values(data: bytes, group_count: int | None, quantity: str) -> list[float | None]:
    """One big-endian IEEE 754 single-precision float per series cell group; NaN is returned as None.

    `group_count` is the number of groups in the cell voltage block, when it was read.
    """
    if not data or len(data) % 4:
        raise CellBlockError(f"{quantity} block of {len(data)} bytes is not a run of 4-byte values")
    count = len(data) // 4
    if group_count is not None and count != group_count:
        raise CellBlockError(f"{quantity} block holds {count} groups, cell voltage block holds {group_count}")
    return [None if math.isnan(value) else value for value in struct.unpack(f">{count}f", data)]


def read_cell_voltages(uds: UdsClient) -> CellVoltages:
    return decode_cell_voltages(uds.read_did(BECM_REQUEST_ID, BECM_RESPONSE_ID, CELL_VOLTAGE_DID))
