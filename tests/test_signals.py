import pytest

from mache_cells.elm327 import Elm327
from mache_cells.signals import read_sensor_temperatures, read_signals
from mache_cells.uds import UdsClient
from tests.conftest import FakeAdapter


def uds_for(adapter: FakeAdapter) -> UdsClient:
    elm = Elm327(adapter, command_timeout_s=1.0, reset_timeout_s=1.0, separation_ms=5, frame_timeout_ms=200)
    elm.initialize()
    return UdsClient(elm)


def test_battery_signals_decode(fake_adapter: FakeAdapter) -> None:
    readings = read_signals(uds_for(fake_adapter))
    values = {reading.key: reading.value for reading in readings if not reading.key.startswith("sensor_")}

    assert values == {
        "odometer": 241570,
        "soh": pytest.approx(91.5),
        "capacity": pytest.approx(253.2),
        "soc_bms": pytest.approx(73.274),
        "soc_display": pytest.approx(79.5),
        "energy_remaining": pytest.approx(60.468),
        "pack_voltage": pytest.approx(356.27),
        "cell_voltage_min": pytest.approx(3.785),
        "cell_voltage_avg": pytest.approx(3.790),
        "battery_age": pytest.approx(65.345),
        "pack_temperature": 3,
        "temperature_max": 6,
        "temperature_min": 3,
        "temperature_avg": 4,
        "coolant_inlet": 10,
    }


def test_sensor_temperatures_decode_to_one_reading_per_sensor(fake_adapter: FakeAdapter) -> None:
    sensors = read_sensor_temperatures(uds_for(fake_adapter))

    assert [(sensor.label, sensor.group, sensor.unit, sensor.decimals) for sensor in sensors] == [
        (f"Sensor {number}", "temperature", "°C", 1) for number in range(1, 9)
    ]
    expected = (3.7745, 3.3005, 3.9232, 3.7371, 3.8676, 3.7558, 5.1990, 4.0889)
    assert [sensor.value for sensor in sensors] == [pytest.approx(value, abs=1e-4) for value in expected]
    assert {reading.key for reading in read_signals(uds_for(fake_adapter))} >= {s.key for s in sensors}


@pytest.mark.parametrize("payload", [None, bytes(31)])
def test_failed_sensor_read_fails_every_sensor(fake_adapter: FakeAdapter, payload: bytes | None) -> None:
    if payload is None:
        del fake_adapter.data[0xFDDC]
    else:
        fake_adapter.data[0xFDDC] = payload

    sensors = read_sensor_temperatures(uds_for(fake_adapter))

    assert len(sensors) == 8
    assert all(sensor.value is None and sensor.error for sensor in sensors)


def test_shared_identifier_is_read_once(fake_adapter: FakeAdapter) -> None:
    read_signals(uds_for(fake_adapter))

    assert fake_adapter.sent.count("224808") == 1


def test_failed_identifier_fails_only_its_signals(fake_adapter: FakeAdapter) -> None:
    del fake_adapter.data[0x4808]

    readings = {reading.key: reading for reading in read_signals(uds_for(fake_adapter))}

    assert readings["temperature_max"].value is None
    assert "requestOutOfRange" in (readings["temperature_max"].error or "")
    assert readings["pack_temperature"].value == 3


def test_short_payload_is_an_error_not_a_value(fake_adapter: FakeAdapter) -> None:
    fake_adapter.data[0x4808] = bytes([56])

    readings = {reading.key: reading for reading in read_signals(uds_for(fake_adapter))}

    assert readings["temperature_max"].value == 6
    assert readings["temperature_avg"].value is None
    assert "need 4" in (readings["temperature_avg"].error or "")
