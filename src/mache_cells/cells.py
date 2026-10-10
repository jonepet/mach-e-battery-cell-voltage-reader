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


def read_cell_voltages(uds: UdsClient) -> list[float | None]:
    return decode_cell_block(uds.read_did(BECM_REQUEST_ID, BECM_RESPONSE_ID, CELL_BLOCK_DID))
