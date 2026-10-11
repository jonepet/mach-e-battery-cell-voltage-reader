import struct
from dataclasses import dataclass

from mache_cells.cells import BECM_REQUEST_ID, BECM_RESPONSE_ID, CellBlockError
from mache_cells.uds import UdsClient

BALANCING_ACTIVE_DID = 0xFDEB
BALANCING_TIME_DID = 0xFDD3
TIMER_TICK_S = 0.2


@dataclass(frozen=True)
class Balancing:
    """Whether each series cell group is being balanced now, and for how long."""

    active: list[bool]
    seconds: list[float]
    active_count: int
    longest_s: float


def decode_balancing(flags: bytes, timers: bytes, group_count: int | None) -> Balancing:
    """`flags` holds one byte per group (1 = balancing); `timers` one big-endian 32-bit count per group
    in 0.2 s ticks since that group started balancing. `group_count` is the number of groups in the cell
    voltage block, when it was read."""
    count = len(flags)
    if not count or len(timers) != count * 4:
        raise CellBlockError(f"{count} balancing flags do not match {len(timers)} timer bytes")
    if group_count is not None and count != group_count:
        raise CellBlockError(f"balancing block holds {count} groups, cell voltage block holds {group_count}")
    active = [flag == 1 for flag in flags]
    seconds = [ticks * TIMER_TICK_S for ticks in struct.unpack(f">{count}I", timers)]
    return Balancing(active=active, seconds=seconds, active_count=sum(active), longest_s=max(seconds))


def read_balancing(uds: UdsClient, group_count: int | None) -> Balancing:
    def read(did: int) -> bytes:
        return uds.read_did(BECM_REQUEST_ID, BECM_RESPONSE_ID, did)

    return decode_balancing(read(BALANCING_ACTIVE_DID), read(BALANCING_TIME_DID), group_count)
