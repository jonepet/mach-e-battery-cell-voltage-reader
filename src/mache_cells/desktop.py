"""Desktop launcher: serve the GUI on this computer only and open it in the default browser."""

import json
import os
import socket
import threading
import time
import urllib.request
import webbrowser
from collections.abc import Callable
from urllib.parse import urlsplit

import uvicorn

from mache_cells.config import Settings
from mache_cells.server import create_app

LOOPBACK = "127.0.0.1"
PROBE_TIMEOUT_S = 1.0
STARTUP_POLL_S = 0.1

OpenUrl = Callable[[str], object]
Serve = Callable[[Settings, Callable[[], None]], None]


def browse_url(settings: Settings) -> str:
    host = LOOPBACK if settings.host in ("", "0.0.0.0") else settings.host
    return f"http://{host}:{settings.port}/"


def reader_running(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url}api/ports", timeout=PROBE_TIMEOUT_S) as response:
            return isinstance(json.load(response), list)
    except (OSError, ValueError):
        return False


def port_in_use(url: str) -> bool:
    address = urlsplit(url)
    with socket.socket() as probe:
        probe.settimeout(PROBE_TIMEOUT_S)
        return probe.connect_ex((address.hostname or LOOPBACK, address.port or 80)) == 0


def serve(settings: Settings, on_started: Callable[[], None]) -> None:
    server = uvicorn.Server(
        uvicorn.Config(create_app(settings), host=settings.host, port=settings.port, log_level="warning")
    )

    def notify() -> None:
        while not server.started and not server.should_exit:
            time.sleep(STARTUP_POLL_S)
        if server.started:
            on_started()

    threading.Thread(target=notify, daemon=True).start()
    server.run()


def launch(settings: Settings, open_url: OpenUrl, serve_gui: Serve) -> int:
    url = browse_url(settings)
    if reader_running(url):
        print(f"The reader is already running. Opening {url}")
        open_url(url)
        return 0
    if port_in_use(url):
        print(
            f"Port {settings.port} is used by another program. Set MACHE_PORT to a free port and start again."
        )
        return 1
    print(f"Mach-E Cell Voltage Reader is running at {url}")
    print("Your browser opens automatically. To stop the reader, close this window or press Ctrl+C.")

    def open_gui() -> None:
        open_url(url)

    serve_gui(settings, open_gui)
    return 0


def main() -> int:
    try:
        settings = Settings.from_env({"MACHE_HOST": LOOPBACK, **os.environ})
    except ValueError as exc:
        print(f"Invalid MACHE_* setting: {exc}")
        input("Press Enter to close.")
        return 1
    code = launch(settings, webbrowser.open, serve)
    if code != 0:
        input("Press Enter to close.")
    return code
