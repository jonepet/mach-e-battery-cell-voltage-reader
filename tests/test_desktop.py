import socket
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from mache_cells.config import Settings
from mache_cells.desktop import browse_url, launch


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


def test_wildcard_bind_address_is_browsed_as_loopback() -> None:
    settings = Settings.from_env({"MACHE_HOST": "0.0.0.0", "MACHE_PORT": "8090"})
    assert browse_url(settings) == "http://127.0.0.1:8090/"


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
