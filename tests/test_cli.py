import json

from mache_cells.__main__ import render_json, render_text
from mache_cells.signals import SignalReading
from mache_cells.stats import analyse

VOLTAGES: list[float | None] = [3.7861, 3.7853, None]
SIGNALS = [
    SignalReading("soh", "State of health", "battery", "%", 1, 91.5, None),
    SignalReading("capacity", "Capacity", "battery", "Ah", 1, None, "service 22 rejected"),
]


def test_text_report_lists_signals_stats_and_every_cell() -> None:
    stats = analyse(VOLTAGES, outlier_deviation=0.02, spread_warning=0.05)

    lines = render_text(VOLTAGES, stats, SIGNALS).splitlines()

    assert lines[:2] == ["State of health: 91.5 %", "Capacity: read failed (service 22 rejected)"]
    assert lines[3].startswith("Cells 2/3: min 3.7853 V (#2), max 3.7861 V (#1)")
    assert lines[4] == "Outliers: none"
    assert lines[-3:] == ["Cell   1: 3.7861 V", "Cell   2: 3.7853 V", "Cell   3: no value"]


def test_json_report_is_machine_readable() -> None:
    document = json.loads(render_json(VOLTAGES, None, SIGNALS))

    assert document["cells"] == VOLTAGES
    assert document["stats"] is None
    assert document["signals"][0]["value"] == 91.5
