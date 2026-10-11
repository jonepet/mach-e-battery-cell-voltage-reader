import struct

import pytest

from mache_cells.cells import CellBlockError, TickWatch, decode_cell_voltages
from mache_cells.stats import analyse
from tests.conftest import CELL_VOLTAGE_HEADER, CELL_VOLTAGES, LIVE_CELLS

REAL_CAR_BLOCK = bytes.fromhex(
    "66d75e8211160003afa24afe000007dc4072f1aa4073126f4072e1484072f1aa4072e1484072e1484072e1484072f46a"
    "4072e148407322d14072e148407322d14072f1aa407333334072e148407334ee4072f1aa407343964072e148407353f8"
    "4072f1aa407343964072f1aa4072f3654072d0e54072c0834072d0e54072b0214072d0e54072d0e54072d0e54073248c"
    "4073020c407343964072f1aa407333334073020c407333334072e14840732efa4072e148407333334072e14840733333"
    "4072e1484072f1aa4072f1aa4072d7454072e1484072e1484072c0834072c0834072e1484072f1aa40729fbe40731c23"
    "4073020c407343964073020c407333334073126f4073126f4073020c407334ee4073020c407333334073020c40734396"
    "4072f1aa407343964073020c407303c84072f1aa407343964072e148407333334072d0e5407353f84072f1aa407334ee"
    "4072f1aa407343964072f1aa407322d14072f1aa407343964072f1aa407319f54072f1aa4073020c4072d0e54072f1aa"
    "4072f1aa40733333"
)


def test_block_holds_the_timestamp_and_94_cells() -> None:
    cells = decode_cell_voltages(CELL_VOLTAGES)

    assert cells.voltages == [pytest.approx(value) for value in LIVE_CELLS]
    assert cells.tick == int.from_bytes(CELL_VOLTAGE_HEADER[:4], "big")


def test_real_car_bytes_decode() -> None:
    cells = decode_cell_voltages(REAL_CAR_BLOCK)

    assert cells.tick == 1725390466
    assert len(cells.voltages) == 94
    assert cells.voltages[:3] == [pytest.approx(3.796), pytest.approx(3.798), pytest.approx(3.795)]
    assert sum(v for v in cells.voltages if v is not None) == pytest.approx(356.917, abs=1e-3)


def test_nan_marks_a_cell_without_measurement() -> None:
    block = CELL_VOLTAGE_HEADER + struct.pack(">f", float("nan")) + struct.pack(">93f", *[3.7] * 93)

    assert decode_cell_voltages(block).voltages[0] is None


@pytest.mark.parametrize("length", [0, 16, 19, 21])
def test_block_that_is_not_a_header_and_4_byte_values_is_rejected(length: int) -> None:
    with pytest.raises(CellBlockError):
        decode_cell_voltages(bytes(length))


def test_age_is_the_time_since_the_timestamp_last_advanced() -> None:
    watch = TickWatch()

    assert watch.age_s(100, now=10.0) == 0
    assert watch.age_s(100, now=12.5) == pytest.approx(2.5)
    assert watch.age_s(112, now=13.0) == 0
    assert watch.age_s(112, now=14.0) == pytest.approx(1.0)


def test_stats_number_cells_from_one_and_flag_outliers() -> None:
    voltages: list[float | None] = [3.71, 3.712, 3.709, 3.65, 3.711, None]

    stats = analyse(voltages, outlier_deviation=0.02, spread_warning=0.05)

    assert stats is not None
    assert (stats.valid, stats.min_cell, stats.max_cell, stats.outliers) == (5, 4, 2, (4,))
    assert stats.spread_exceeded


def test_stats_of_no_readings_is_none() -> None:
    assert analyse([None, None], outlier_deviation=0.02, spread_warning=0.05) is None
