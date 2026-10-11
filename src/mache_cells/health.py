import statistics
from dataclasses import dataclass

from mache_cells.cells import BECM_REQUEST_ID, BECM_RESPONSE_ID, decode_group_values
from mache_cells.uds import UdsClient

GROUP_CAPACITY_DID = 0xFDCD


@dataclass(frozen=True)
class GroupHealth:
    """Capacity of each series cell group and its state of health against the pack's 100 % capacity.

    The 100 % capacity is the BMS pack capacity divided by the BMS pack state of health; `health` is None
    for every group when either pack value is missing.
    """

    capacities: list[float | None]
    reference_capacity: float | None
    health: list[float | None]
    minimum: float
    maximum: float
    mean: float
    weakest_group: int
    strongest_group: int


def read_group_capacities(uds: UdsClient, group_count: int | None) -> list[float | None]:
    """Capacity in Ah of each series cell group."""
    data = uds.read_did(BECM_REQUEST_ID, BECM_RESPONSE_ID, GROUP_CAPACITY_DID)
    return decode_group_values(data, group_count, "capacity")


def analyse_health(
    capacities: list[float | None], pack_capacity: float | None, pack_health: float | None
) -> GroupHealth | None:
    """Summarise group capacities; groups are numbered from 1."""
    numbered = [(number, value) for number, value in enumerate(capacities, start=1) if value is not None]
    if not numbered:
        return None
    reference = pack_capacity / pack_health * 100 if pack_capacity and pack_health else None
    weakest_group, minimum = min(numbered, key=lambda pair: pair[1])
    strongest_group, maximum = max(numbered, key=lambda pair: pair[1])
    return GroupHealth(
        capacities=capacities,
        reference_capacity=reference,
        health=[
            None if value is None or reference is None else value / reference * 100 for value in capacities
        ],
        minimum=minimum,
        maximum=maximum,
        mean=statistics.fmean(value for _, value in numbered),
        weakest_group=weakest_group,
        strongest_group=strongest_group,
    )
