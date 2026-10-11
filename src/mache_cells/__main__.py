"""Read every cell voltage of a Ford Mustang Mach-E high-voltage battery through an ELM327/STN adapter."""

import argparse
import json
import os
import sys
from collections.abc import Callable
from dataclasses import asdict

import uvicorn

from mache_cells.cells import CellBlockError, read_cell_voltages
from mache_cells.config import Settings
from mache_cells.elm327 import AdapterError, Elm327
from mache_cells.server import create_app
from mache_cells.signals import SignalReading, read_signals
from mache_cells.stats import CellStats, analyse
from mache_cells.transport import SerialTransport, TransportError
from mache_cells.uds import UdsClient, UdsError


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("serve", help="run the web GUI")
    read = commands.add_parser("read", help="read the battery once and print it")
    read.add_argument("port", help="adapter serial port, e.g. /dev/ttyUSB0")
    read.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = parser.parse_args()

    settings = Settings.from_env(os.environ)
    if args.command == "serve":
        uvicorn.run(create_app(settings), host=settings.host, port=settings.port)
        return
    sys.exit(read_once(settings, args.port, render_json if args.json else render_text))


Renderer = Callable[[list[float | None], CellStats | None, list[SignalReading]], str]


def read_once(settings: Settings, port: str, render: Renderer) -> int:
    try:
        adapter = Elm327(
            SerialTransport(port, settings.baudrate),
            settings.command_timeout_s,
            settings.reset_timeout_s,
            settings.separation_ms,
            settings.frame_timeout_ms,
        )
    except TransportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    try:
        adapter.initialize()
        uds = UdsClient(adapter)
        voltages = read_cell_voltages(uds).voltages
        signals = read_signals(uds)
    except (TransportError, AdapterError, UdsError, CellBlockError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        adapter.close()
    stats = analyse(voltages, settings.outlier_deviation_v, settings.spread_warning_v)
    print(render(voltages, stats, signals))
    return 0


def render_json(voltages: list[float | None], stats: CellStats | None, signals: list[SignalReading]) -> str:
    document = {
        "cells": voltages,
        "stats": None if stats is None else asdict(stats),
        "signals": [asdict(signal) for signal in signals],
    }
    return json.dumps(document, indent=2)


def render_text(voltages: list[float | None], stats: CellStats | None, signals: list[SignalReading]) -> str:
    lines = [_signal_line(signal) for signal in signals]
    if stats is not None:
        lines += [
            "",
            f"Cells {stats.valid}/{len(voltages)}: min {stats.minimum:.4f} V (#{stats.min_cell}), "
            f"max {stats.maximum:.4f} V (#{stats.max_cell}), mean {stats.mean:.4f} V, "
            f"spread {stats.spread * 1000:.1f} mV, std. deviation {stats.stdev * 1000:.1f} mV",
            f"Outliers: {', '.join(f'#{cell}' for cell in stats.outliers) or 'none'}",
        ]
    lines += ["", *(_cell_line(number, value) for number, value in enumerate(voltages, start=1))]
    return "\n".join(lines)


def _signal_line(signal: SignalReading) -> str:
    if signal.value is None:
        return f"{signal.label}: read failed ({signal.error})"
    return f"{signal.label}: {signal.value:.{signal.decimals}f} {signal.unit}"


def _cell_line(number: int, value: float | None) -> str:
    return f"Cell {number:3d}: {'no value' if value is None else f'{value:.4f} V'}"


if __name__ == "__main__":
    main()
