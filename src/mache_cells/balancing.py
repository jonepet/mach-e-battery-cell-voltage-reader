import statistics
import struct
from dataclasses import dataclass

from mache_cells.cells import BECM_REQUEST_ID, BECM_RESPONSE_ID, CellBlockError, decode_group_values
from mache_cells.uds import UdsClient

GROUP_CHARGE_DID = 0xFDCE
BALANCING_ACTIVE_DID = 0xFDEB
BALANCING_TIME_DID = 0xFDD3
TIMER_TICK_S = 0.2


@dataclass(frozen=True)
class Balancing:
    """State of charge of each series cell group, and whether it is being balanced now and for how long.

    The charge summary is None when no group reports a state of charge.
    """

    charge: list[float | None]
    charge_mean: float | None
    charge_min: float | None
    charge_max: float | None
    active: list[bool]
    seconds: list[float]
    active_count: int
    longest_s: float


def decode_balancing(charge: list[float | None], flags: bytes, timers: bytes) -> Balancing:
    """`flags` holds one byte per group (1 = balancing); `timers` one big-endian 32-bit count per group
    in 0.2 s ticks since that group started balancing."""
    count = len(flags)
    if not count or len(timers) != count * 4 or len(charge) != count:
        raise CellBlockError(
            f"{count} balancing flags do not match {len(timers)} timer bytes and {len(charge)} charge values"
        )
    active = [flag == 1 for flag in flags]
    seconds = [ticks * TIMER_TICK_S for ticks in struct.unpack(f">{count}I", timers)]
    valid = [value for value in charge if value is not None]
    return Balancing(
        charge=charge,
        charge_mean=statistics.fmean(valid) if valid else None,
        charge_min=min(valid, default=None),
        charge_max=max(valid, default=None),
        active=active,
        seconds=seconds,
        active_count=sum(active),
        longest_s=max(seconds),
    )


def read_balancing(uds: UdsClient, group_count: int | None) -> Balancing:
    def read(did: int) -> bytes:
        return uds.read_did(BECM_REQUEST_ID, BECM_RESPONSE_ID, did)

    charge = decode_group_values(read(GROUP_CHARGE_DID), group_count, "state of charge")
    return decode_balancing(charge, read(BALANCING_ACTIVE_DID), read(BALANCING_TIME_DID))
