import pytest

from mache_cells.balancing import decode_balancing
from mache_cells.cells import CellBlockError, decode_group_values
from tests.conftest import BALANCING_GROUPS, BECM_DATA, GROUP_CHARGE


def test_charge_flags_and_timers_give_balancing_per_group() -> None:
    charge = decode_group_values(BECM_DATA[0xFDCE], 94, "state of charge")

    balancing = decode_balancing(charge, BECM_DATA[0xFDEB], BECM_DATA[0xFDD3])

    assert [group for group in range(1, 95) if balancing.active[group - 1]] == sorted(BALANCING_GROUPS)
    assert balancing.active_count == len(BALANCING_GROUPS)
    assert balancing.seconds[0] == pytest.approx(960.4)
    assert balancing.seconds[2] == 0
    assert balancing.longest_s == pytest.approx(960.4)
    assert balancing.charge_max == pytest.approx(max(GROUP_CHARGE))
    assert balancing.charge_mean == pytest.approx(sum(GROUP_CHARGE) / 94, abs=1e-4)


def test_real_car_bytes_decode() -> None:
    charge = decode_group_values(bytes.fromhex("426e70e1426e6a45"), None, "state of charge")

    balancing = decode_balancing(charge, bytes.fromhex("0100"), bytes.fromhex("000012c200000000"))

    assert balancing.charge == [pytest.approx(59.61, abs=1e-2), pytest.approx(59.60, abs=1e-2)]
    assert balancing.active == [True, False]
    assert balancing.seconds == [pytest.approx(960.4), 0]


def test_groups_without_charge_leave_no_charge_summary() -> None:
    balancing = decode_balancing([None, None], bytes(2), bytes(8))

    assert (balancing.charge_mean, balancing.charge_min, balancing.charge_max) == (None, None, None)


@pytest.mark.parametrize(
    ("charge", "flags", "timers"),
    [([], b"", b""), ([59.0, 59.0], bytes(2), bytes(4)), ([59.0], bytes(2), bytes(8))],
)
def test_blocks_that_disagree_on_group_count_are_rejected(
    charge: list[float | None], flags: bytes, timers: bytes
) -> None:
    with pytest.raises(CellBlockError):
        decode_balancing(charge, flags, timers)
