import re
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from mache_cells.config import Settings
from mache_cells.server import create_app
from mache_cells.transport import Transport
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
    assert reading["stats"]["valid"] == 94
    assert reading["stats"]["min_cell"] == 9
    signals = {signal["key"]: signal for signal in reading["signals"]}
    assert signals["soh"]["value"] == pytest.approx(91.5)
    assert all(signal["error"] is None for signal in reading["signals"])


def test_failed_cell_read_keeps_battery_signals(client: TestClient, port: str, adapter: FakeAdapter) -> None:
    del adapter.data[0xFDF4]
    client.put("/api/connection", json={"port": port})

    reading = wait_for(client, lambda s: s["reading"] is not None)["reading"]

    assert reading["voltages"] == []
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


@pytest.mark.parametrize(("separation", "frame_timeout"), [("200", "300"), ("20", "20"), ("5", "2000")])
def test_inconsistent_timing_is_rejected_at_startup(separation: str, frame_timeout: str) -> None:
    env = {"MACHE_SEPARATION_MS": separation, "MACHE_FRAME_TIMEOUT_MS": frame_timeout}

    with pytest.raises(ValueError, match="ms"):
        Settings.from_env(env)


def test_unknown_port_is_rejected(client: TestClient) -> None:
    assert client.put("/api/connection", json={"port": "/etc/passwd"}).status_code == 422


def test_gui_is_served(client: TestClient) -> None:
    page = client.get("/")

    assert page.status_code == 200
    assert "Mach-E Cell Voltages" in page.text
