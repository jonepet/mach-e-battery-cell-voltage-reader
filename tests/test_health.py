import struct

import pytest

from mache_cells.cells import CellBlockError, decode_group_values
from mache_cells.health import analyse_health
from tests.conftest import BECM_DATA, GROUP_CAPACITIES


def test_capacity_block_holds_one_float_per_group() -> None:
    assert decode_group_values(BECM_DATA[0xFDCD], 94, "capacity") == [
        pytest.approx(value) for value in GROUP_CAPACITIES
    ]


def test_real_car_bytes_decode() -> None:
    assert decode_group_values(bytes.fromhex("4378D70A"), None, "capacity") == [
        pytest.approx(248.84, abs=1e-2)
    ]


def test_nan_marks_a_group_without_a_value() -> None:
    assert decode_group_values(struct.pack(">2f", float("nan"), 250.0), 2, "capacity") == [None, 250.0]


@pytest.mark.parametrize("length", [0, 5])
def test_block_that_is_not_4_byte_values_is_rejected(length: int) -> None:
    with pytest.raises(CellBlockError):
        decode_group_values(bytes(length), None, "capacity")


def test_group_count_must_match_the_cell_block() -> None:
    with pytest.raises(CellBlockError, match="capacity block holds 96 groups"):
        decode_group_values(struct.pack(">96f", *[250.0] * 96), 94, "capacity")


def test_group_health_is_capacity_against_the_pack_capacity_at_100_percent() -> None:
    health = analyse_health([250.0, None, 260.0], pack_capacity=253.0, pack_health=92.0)

    assert health is not None
    assert health.reference_capacity == pytest.approx(275.0)
    assert health.health == [pytest.approx(250 / 2.75), None, pytest.approx(260 / 2.75)]
    assert (health.weakest_group, health.strongest_group, health.mean) == (1, 3, pytest.approx(255.0))


def test_missing_pack_values_leave_capacities_without_health() -> None:
    health = analyse_health([250.0, 251.0], pack_capacity=None, pack_health=92.0)

    assert health is not None
    assert health.reference_capacity is None
    assert health.health == [None, None]


def test_no_capacities_is_none() -> None:
    assert analyse_health([None], pack_capacity=253.0, pack_health=92.0) is None
