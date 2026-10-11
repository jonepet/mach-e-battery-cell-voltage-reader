import socket
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from mache_cells.config import Settings
from mache_cells.desktop import NETWORK_ACCESS_MARKER, browse_url, launch, launch_environment, network_urls


class ReaderHandler(BaseHTTPRequestHandler):
    body = b'["COM3"]'

    def do_GET(self) -> None:
        self.send_response(200)
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, format: str, *args: object) -> None:
        pass


def settings_for(port: int) -> Settings:
    return Settings.from_env({"MACHE_HOST": "127.0.0.1", "MACHE_PORT": str(port)})


@pytest.fixture
def http_server() -> Iterator[HTTPServer]:
    server = HTTPServer(("127.0.0.1", 0), ReaderHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()
    server.server_close()


@pytest.fixture
def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def test_default_settings_are_browsed_on_loopback() -> None:
    assert browse_url(Settings.from_env({"MACHE_PORT": "8090"})) == "http://127.0.0.1:8090/"


def test_wildcard_bind_address_is_browsed_as_loopback() -> None:
    settings = Settings.from_env({"MACHE_HOST": "0.0.0.0", "MACHE_PORT": "8090"})
    assert browse_url(settings) == "http://127.0.0.1:8090/"


def test_ipv6_wildcard_is_browsed_as_loopback() -> None:
    assert (
        browse_url(Settings.from_env({"MACHE_HOST": "::", "MACHE_PORT": "8090"})) == "http://127.0.0.1:8090/"
    )


def test_network_urls_list_the_own_hosts_when_listening_on_all_interfaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("mache_cells.desktop.local_hosts", lambda: ("my-pc", "192.168.1.20", "[fd00::20]"))
    settings = Settings.from_env({"MACHE_HOST": "0.0.0.0", "MACHE_PORT": "8090"})

    assert network_urls(settings) == [
        "http://my-pc:8090/",
        "http://192.168.1.20:8090/",
        "http://[fd00::20]:8090/",
    ]


def test_network_urls_are_empty_on_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mache_cells.desktop.local_hosts", lambda: ("my-pc",))

    assert network_urls(Settings.from_env({})) == []


def test_launch_prints_the_network_addresses_in_network_mode(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], free_port: int
) -> None:
    monkeypatch.setattr("mache_cells.desktop.local_hosts", lambda: ("my-pc", "192.168.1.20"))
    settings = Settings.from_env({"MACHE_HOST": "0.0.0.0", "MACHE_PORT": str(free_port)})

    launch(settings, lambda url: None, lambda settings, on_started: None)

    output = capsys.readouterr().out
    assert f"  http://my-pc:{free_port}/" in output
    assert f"  http://192.168.1.20:{free_port}/" in output


def test_launch_prints_no_network_addresses_on_loopback(
    capsys: pytest.CaptureFixture[str], free_port: int
) -> None:
    launch(settings_for(free_port), lambda url: None, lambda settings, on_started: None)

    assert "Other devices" not in capsys.readouterr().out


def test_marker_file_switches_the_default_to_all_interfaces(tmp_path: Path) -> None:
    (tmp_path / NETWORK_ACCESS_MARKER).touch()

    assert launch_environment({"MACHE_PORT": "9000"}, tmp_path) == {
        "MACHE_PORT": "9000",
        "MACHE_HOST": "0.0.0.0",
    }


def test_explicit_host_overrides_the_marker_file(tmp_path: Path) -> None:
    (tmp_path / NETWORK_ACCESS_MARKER).touch()

    assert launch_environment({"MACHE_HOST": "127.0.0.1"}, tmp_path) == {"MACHE_HOST": "127.0.0.1"}


def test_without_marker_file_the_environment_is_unchanged(tmp_path: Path) -> None:
    assert launch_environment({"MACHE_PORT": "9000"}, tmp_path) == {"MACHE_PORT": "9000"}


def test_free_port_starts_the_server_and_opens_the_browser_once_started(free_port: int) -> None:
    opened: list[str] = []

    def serve(settings: Settings, on_started: object) -> None:
        assert opened == []
        assert callable(on_started)
        on_started()

    code = launch(settings_for(free_port), opened.append, serve)

    assert code == 0
    assert opened == [f"http://127.0.0.1:{free_port}/"]


def test_running_reader_is_not_started_twice(http_server: HTTPServer) -> None:
    opened: list[str] = []
    started: list[Settings] = []
    port = http_server.server_address[1]

    code = launch(settings_for(port), opened.append, lambda settings, _: started.append(settings))

    assert code == 0
    assert opened == [f"http://127.0.0.1:{port}/"]
    assert started == []


def test_port_held_by_another_program_is_an_error(
    http_server: HTTPServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ReaderHandler, "body", b"<html></html>")
    opened: list[str] = []
    started: list[Settings] = []

    code = launch(
        settings_for(http_server.server_address[1]),
        opened.append,
        lambda settings, _: started.append(settings),
    )

    assert code == 1
    assert opened == []
    assert started == []
