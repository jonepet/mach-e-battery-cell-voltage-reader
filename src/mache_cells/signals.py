import math
import struct
from dataclasses import dataclass

from mache_cells.cells import BECM_REQUEST_ID, BECM_RESPONSE_ID
from mache_cells.elm327 import AdapterError
from mache_cells.uds import UdsClient, UdsError

SENSOR_TEMPERATURE_DID = 0xFDDC
SENSOR_COUNT = 8


@dataclass(frozen=True)
class Signal:
    """One value: `length` big-endian bytes at `offset` in the identifier's data, times scale plus add."""

    key: str
    label: str
    group: str
    did: int
    unit: str
    decimals: int
    scale: float = 1.0
    add: float = 0.0
    offset: int = 0
    length: int = 1

    def decode(self, data: bytes) -> float:
        end = self.offset + self.length
        if len(data) < end:
            raise ValueError(f"{self.did:04X} returned {len(data)} bytes, need {end}")
        return int.from_bytes(data[self.offset : end], "big") * self.scale + self.add


@dataclass(frozen=True)
class SignalReading:
    key: str
    label: str
    group: str
    unit: str
    decimals: int
    value: float | None
    error: str | None


SIGNALS = (
    Signal("odometer", "Odometer", "vehicle", 0xDD01, "km", 0, length=3),
    Signal("soh", "State of health", "battery", 0x490C, "%", 1, scale=0.5),
    Signal("capacity", "Capacity", "battery", 0x485C, "Ah", 1, scale=0.1, length=2),
    Signal("soc_bms", "State of charge (BMS)", "battery", 0x4801, "%", 1, scale=0.002, length=2),
    Signal("soc_display", "State of charge (displayed)", "battery", 0x4845, "%", 1, scale=0.5),
    Signal("energy_remaining", "Energy remaining", "battery", 0x4848, "kWh", 2, scale=0.002, length=2),
    Signal("pack_voltage", "Pack voltage", "battery", 0x480D, "V", 1, scale=0.01, length=2),
    Signal("cell_voltage_min", "Lowest cell voltage", "battery", 0x4840, "V", 3, scale=0.001, length=2),
    Signal("cell_voltage_avg", "Average cell voltage", "battery", 0x4841, "V", 3, scale=0.001, length=2),
    Signal("battery_age", "Battery age", "battery", 0x4810, "months", 1, scale=0.005, length=2),
    Signal("pack_temperature", "Pack temperature", "temperature", 0x4800, "°C", 0, add=-50),
    Signal("temperature_max", "Highest sensor temperature", "temperature", 0x4808, "°C", 0, add=-50),
    Signal("temperature_min", "Lowest sensor temperature", "temperature", 0x4808, "°C", 0, add=-50, offset=1),
    Signal(
        "temperature_avg", "Average sensor temperature", "temperature", 0x4808, "°C", 0, add=-50, offset=3
    ),
    Signal("coolant_inlet", "Coolant inlet temperature", "temperature", 0x4846, "°C", 0, add=-50),
)


def read_signals(uds: UdsClient) -> list[SignalReading]:
    """Read every signal, each identifier once; a failed identifier fails only the signals that use it."""
    replies: dict[int, bytes | str] = {}
    for did in dict.fromkeys(signal.did for signal in SIGNALS):
        try:
            replies[did] = uds.read_did(BECM_REQUEST_ID, BECM_RESPONSE_ID, did)
        except (AdapterError, UdsError) as exc:
            replies[did] = str(exc)
    return [*(_reading(signal, replies[signal.did]) for signal in SIGNALS), *read_sensor_temperatures(uds)]


def read_sensor_temperatures(uds: UdsClient) -> list[SignalReading]:
    """One reading per battery temperature sensor; a failed read fails all of them."""
    values: list[float | None] = [None] * SENSOR_COUNT
    error = None
    try:
        data = uds.read_did(BECM_REQUEST_ID, BECM_RESPONSE_ID, SENSOR_TEMPERATURE_DID)
        if len(data) != SENSOR_COUNT * 4:
            raise ValueError(
                f"{SENSOR_TEMPERATURE_DID:04X} returned {len(data)} bytes, need {SENSOR_COUNT * 4}"
            )
        values = [None if math.isnan(value) else value for value in struct.unpack(f">{SENSOR_COUNT}f", data)]
    except (AdapterError, UdsError, ValueError) as exc:
        error = str(exc)
    return [
        SignalReading(f"sensor_{number}", f"Sensor {number}", "temperature", "°C", 1, value, error)
        for number, value in enumerate(values, start=1)
    ]


def _reading(signal: Signal, reply: bytes | str) -> SignalReading:
    value: float | None = None
    error = reply if isinstance(reply, str) else None
    if isinstance(reply, bytes):
        try:
            value = signal.decode(reply)
        except ValueError as exc:
            error = str(exc)
    return SignalReading(signal.key, signal.label, signal.group, signal.unit, signal.decimals, value, error)
