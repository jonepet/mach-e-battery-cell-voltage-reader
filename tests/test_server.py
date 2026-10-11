import re
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from serial.tools import list_ports

from mache_cells.config import Settings
from mache_cells.server import create_app
from mache_cells.transport import PortBusy, Transport
from tests.conftest import BECM_DATA, FakeAdapter


@pytest.fixture
def port(tmp_path: Path) -> str:
    device = tmp_path / "ttyUSB0"
    device.touch()
    return str(device)


@pytest.fixture
def adapter() -> FakeAdapter:
    return FakeAdapter(dict(BECM_DATA))


@pytest.fixture
def client(tmp_path: Path, adapter: FakeAdapter) -> Iterator[TestClient]:
    settings = Settings.from_env(
        {"MACHE_READ_INTERVAL_S": "0.05", "MACHE_PORT_PATTERNS": str(tmp_path / "tty*")}
    )

    def open_transport(port: str, baudrate: int) -> Transport:
        return adapter

    with TestClient(create_app(settings, open_transport)) as test_client:
        yield test_client


def wait_for(client: TestClient, condition: Callable[[dict[str, Any]], bool]) -> dict[str, Any]:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        state: dict[str, Any] = client.get("/api/state").json()
        if condition(state):
            return state
        time.sleep(0.05)
    raise AssertionError(f"condition not met; last status {state['status']}")


def test_connection_reads_every_cell_and_battery_signal(client: TestClient, port: str) -> None:
    assert client.get("/api/ports").json() == [port]
    client.put("/api/connection", json={"port": port})

    reading = wait_for(client, lambda s: s["reading"] is not None)["reading"]

    assert len(reading["voltages"]) == 94
    assert reading["cell_error"] is None
    assert reading["voltages_age_s"] >= 0
    assert reading["stats"]["valid"] == 94
    assert reading["stats"]["min_cell"] == 9
    signals = {signal["key"]: signal for signal in reading["signals"]}
    assert signals["soh"]["value"] == pytest.approx(91.5)
    assert all(signal["error"] is None for signal in reading["signals"])
    assert reading["health_error"] is None
    assert reading["health"]["weakest_group"] == 20
    assert reading["health"]["reference_capacity"] == pytest.approx(253.2 / 0.915)
    assert reading["health"]["health"][19] == pytest.approx(248.84 / (253.2 / 0.915) * 100)
    assert reading["balancing_error"] is None
    assert reading["balancing"]["active_count"] == 4
    assert reading["balancing"]["active"][0] is True


def test_failed_capacity_read_keeps_cell_voltages(
    client: TestClient, port: str, adapter: FakeAdapter
) -> None:
    del adapter.data[0xFDCD]
    client.put("/api/connection", json={"port": port})

    reading = wait_for(client, lambda s: s["reading"] is not None)["reading"]

    assert len(reading["voltages"]) == 94
    assert reading["health"] is None
    assert "requestOutOfRange" in reading["health_error"]


def test_failed_cell_read_keeps_battery_signals(client: TestClient, port: str, adapter: FakeAdapter) -> None:
    del adapter.data[0xFDE3]
    client.put("/api/connection", json={"port": port})

    reading = wait_for(client, lambda s: s["reading"] is not None)["reading"]

    assert reading["voltages"] == []
    assert reading["voltages_age_s"] is None
    assert "requestOutOfRange" in reading["cell_error"]
    assert reading["stats"] is None
    assert next(s for s in reading["signals"] if s["key"] == "soh")["value"] == pytest.approx(91.5)


def test_vehicle_only_receives_read_requests(client: TestClient, port: str, adapter: FakeAdapter) -> None:
    client.put("/api/connection", json={"port": port})
    wait_for(client, lambda s: s["reading"] is not None)
    client.delete("/api/connection")

    vehicle_requests = [command for command in adapter.sent if not command.startswith(("AT", "ST"))]
    assert vehicle_requests
    assert all(re.fullmatch(r"22[0-9A-F]{4}", command) for command in vehicle_requests)
    assert adapter.closed


def test_disconnect_stops_reading(client: TestClient, port: str, adapter: FakeAdapter) -> None:
    client.put("/api/connection", json={"port": port})
    wait_for(client, lambda s: s["reading"] is not None)

    assert client.delete("/api/connection").json()["status"] == "disconnected"
    assert adapter.closed
    assert client.get("/api/state").json()["status"] == "disconnected"
    assert adapter.sent_after_close == []


def test_state_changes_and_readings_are_pushed(client: TestClient, port: str) -> None:
    with client.websocket_connect("/api/events") as events:
        assert events.receive_json()["status"] == "disconnected"

        client.put("/api/connection", json={"port": port})
        state = events.receive_json()
        while state["reading"] is None:
            state = events.receive_json()

        assert state["status"] == "connected"
        assert len(state["reading"]["voltages"]) == 94

        client.delete("/api/connection")
        while state["status"] != "disconnected":
            state = events.receive_json()


def test_pushed_state_matches_the_state_endpoint(client: TestClient) -> None:
    with client.websocket_connect("/api/events") as events:
        assert events.receive_json() == client.get("/api/state").json()


@pytest.mark.parametrize(("separation", "frame_timeout"), [("200", "300"), ("20", "20"), ("5", "2000")])
def test_inconsistent_timing_is_rejected_at_startup(separation: str, frame_timeout: str) -> None:
    env = {"MACHE_SEPARATION_MS": separation, "MACHE_FRAME_TIMEOUT_MS": frame_timeout}

    with pytest.raises(ValueError, match="ms"):
        Settings.from_env(env)


def test_serial_ports_listed_by_the_system_are_offered(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    listed = [SimpleNamespace(device="COM3"), SimpleNamespace(device="COM7"), SimpleNamespace(device="LPT1")]
    monkeypatch.setattr(list_ports, "comports", lambda: listed)
    (tmp_path / "COMfile.dll").touch()
    monkeypatch.chdir(tmp_path)
    settings = Settings.from_env({"MACHE_PORT_PATTERNS": "COM*"})

    with TestClient(create_app(settings)) as test_client:
        assert test_client.get("/api/ports").json() == ["COM3", "COM7"]


def test_port_held_by_another_program_is_reported_as_busy(tmp_path: Path, port: str) -> None:
    settings = Settings.from_env({"MACHE_PORT_PATTERNS": str(tmp_path / "tty*")})

    def held(port: str, baudrate: int) -> Transport:
        raise PortBusy(f"cannot open {port}")

    with TestClient(create_app(settings, held)) as test_client:
        assert test_client.put("/api/connection", json={"port": port}).json()["status"] == "port_busy"


def test_unknown_port_is_rejected(client: TestClient) -> None:
    assert client.put("/api/connection", json={"port": "/etc/passwd"}).status_code == 422


def test_gui_is_served(client: TestClient) -> None:
    page = client.get("/")

    assert page.status_code == 200
    assert "Mach-E Cell Voltages" in page.text
