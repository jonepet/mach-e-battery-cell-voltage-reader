import math
import struct

from mache_cells.uds import UdsClient

BECM_REQUEST_ID = 0x7E4
BECM_RESPONSE_ID = 0x7EC
CELL_BLOCK_DID = 0xFDF4


class CellBlockError(Exception):
    pass


def decode_cell_block(data: bytes) -> list[float | None]:
    """Cell voltages from the BECM cell block.

    The block holds three equal runs of big-endian IEEE 754 single-precision floats, one value per cell
    (94 on the extended-range pack); the first run is the live cell voltage. NaN is returned as None.
    """
    if not data or len(data) % 12:
        raise CellBlockError(f"cell block of {len(data)} bytes is not three runs of 4-byte values")
    count = len(data) // 12
    floats = struct.unpack(f">{count}f", data[: count * 4])
    return [None if math.isnan(value) else value for value in floats]


def decode_group_values(data: bytes, group_count: int | None, quantity: str) -> list[float | None]:
    """One big-endian IEEE 754 single-precision float per series cell group; NaN is returned as None.

    `group_count` is the number of groups in the cell block, when it was read.
    """
    if not data or len(data) % 4:
        raise CellBlockError(f"{quantity} block of {len(data)} bytes is not a run of 4-byte values")
    count = len(data) // 4
    if group_count is not None and count != group_count:
        raise CellBlockError(f"{quantity} block holds {count} groups, cell block holds {group_count}")
    return [None if math.isnan(value) else value for value in struct.unpack(f">{count}f", data)]


def read_cell_voltages(uds: UdsClient) -> list[float | None]:
    return decode_cell_block(uds.read_did(BECM_REQUEST_ID, BECM_RESPONSE_ID, CELL_BLOCK_DID))
