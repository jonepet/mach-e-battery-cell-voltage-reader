import statistics
from dataclasses import dataclass


@dataclass(frozen=True)
class CellStats:
    valid: int
    minimum: float
    maximum: float
    mean: float
    median: float
    stdev: float
    spread: float
    min_cell: int
    max_cell: int
    outliers: tuple[int, ...]
    spread_exceeded: bool


def analyse(
    voltages: list[float | None], outlier_deviation: float, spread_warning: float
) -> CellStats | None:
    """Summarise cell voltages; cells are numbered from 1, outliers deviate from the median by more than
    outlier_deviation volts."""
    numbered = [(number, value) for number, value in enumerate(voltages, start=1) if value is not None]
    if not numbered:
        return None
    readings = [value for _, value in numbered]
    median = statistics.median(readings)
    min_cell, minimum = min(numbered, key=lambda pair: pair[1])
    max_cell, maximum = max(numbered, key=lambda pair: pair[1])
    return CellStats(
        valid=len(readings),
        minimum=minimum,
        maximum=maximum,
        mean=statistics.fmean(readings),
        median=median,
        stdev=statistics.pstdev(readings),
        spread=maximum - minimum,
        min_cell=min_cell,
        max_cell=max_cell,
        outliers=tuple(number for number, value in numbered if abs(value - median) > outlier_deviation),
        spread_exceeded=maximum - minimum > spread_warning,
    )
