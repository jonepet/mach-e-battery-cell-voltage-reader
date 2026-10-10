import struct

import pytest

from mache_cells.cells import CellBlockError, decode_cell_block
from mache_cells.stats import analyse
from tests.conftest import CELL_BLOCK, LIVE_CELLS


def test_extended_range_block_holds_94_cells() -> None:
    assert decode_cell_block(CELL_BLOCK) == [pytest.approx(value) for value in LIVE_CELLS]


def test_cell_count_follows_block_length() -> None:
    block = struct.pack(">288f", *[3.7] * 288)

    assert len(decode_cell_block(block)) == 96


def test_real_car_bytes_decode() -> None:
    block = bytes.fromhex("4072D0E54072B021") + bytes(1120)

    assert decode_cell_block(block)[:2] == [pytest.approx(3.7940, abs=1e-4), pytest.approx(3.7920, abs=1e-4)]


def test_nan_marks_a_cell_without_measurement() -> None:
    block = struct.pack(">f", float("nan")) + struct.pack(">281f", *[3.7] * 281)

    assert decode_cell_block(block)[0] is None


@pytest.mark.parametrize("length", [0, 13, 1131])
def test_block_that_is_not_three_runs_is_rejected(length: int) -> None:
    with pytest.raises(CellBlockError):
        decode_cell_block(bytes(length))


def test_stats_number_cells_from_one_and_flag_outliers() -> None:
    voltages: list[float | None] = [3.71, 3.712, 3.709, 3.65, 3.711, None]

    stats = analyse(voltages, outlier_deviation=0.02, spread_warning=0.05)

    assert stats is not None
    assert (stats.valid, stats.min_cell, stats.max_cell, stats.outliers) == (5, 4, 2, (4,))
    assert stats.spread_exceeded


def test_stats_of_no_readings_is_none() -> None:
    assert analyse([None, None], outlier_deviation=0.02, spread_warning=0.05) is None
