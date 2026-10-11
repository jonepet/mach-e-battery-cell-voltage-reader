import pytest

from mache_cells.balancing import decode_balancing
from mache_cells.cells import CellBlockError
from tests.conftest import BALANCING_GROUPS, BECM_DATA


def test_flags_and_timers_give_balancing_per_group() -> None:
    balancing = decode_balancing(BECM_DATA[0xFDEB], BECM_DATA[0xFDD3], 94)

    assert [group for group in range(1, 95) if balancing.active[group - 1]] == sorted(BALANCING_GROUPS)
    assert balancing.active_count == len(BALANCING_GROUPS)
    assert balancing.seconds[0] == pytest.approx(960.4)
    assert balancing.seconds[2] == 0
    assert balancing.longest_s == pytest.approx(960.4)


def test_real_car_bytes_decode() -> None:
    balancing = decode_balancing(bytes.fromhex("0100"), bytes.fromhex("000012c200000000"), None)

    assert balancing.active == [True, False]
    assert balancing.seconds == [pytest.approx(960.4), 0]


@pytest.mark.parametrize(
    ("flags", "timers", "group_count"),
    [(b"", b"", None), (bytes(2), bytes(4), None), (bytes(2), bytes(8), 94)],
)
def test_blocks_that_disagree_on_group_count_are_rejected(
    flags: bytes, timers: bytes, group_count: int | None
) -> None:
    with pytest.raises(CellBlockError):
        decode_balancing(flags, timers, group_count)
