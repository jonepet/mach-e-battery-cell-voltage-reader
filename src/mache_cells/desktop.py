"""Desktop launcher: serve the GUI and open it in the default browser."""

import json
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from collections.abc import Callable, Mapping
from pathlib import Path
from urllib.parse import urlsplit

import uvicorn

from mache_cells.config import Settings
from mache_cells.network import listens_on_all_interfaces, local_hosts
from mache_cells.server import create_app

LOOPBACK = "127.0.0.1"
NETWORK_ACCESS_MARKER = "network-access.enabled"
PROBE_TIMEOUT_S = 1.0
STARTUP_POLL_S = 0.1

OpenUrl = Callable[[str], object]
Serve = Callable[[Settings, Callable[[], None]], None]


def browse_url(settings: Settings) -> str:
    host = LOOPBACK if listens_on_all_interfaces(settings.host) else settings.host
    return f"http://{host}:{settings.port}/"


def network_urls(settings: Settings) -> list[str]:
    if not listens_on_all_interfaces(settings.host):
        return []
    return [f"http://{host}:{settings.port}/" for host in local_hosts()]


def launch_environment(environ: Mapping[str, str], app_dir: Path) -> dict[str, str]:
    """The installer creates the marker file when network access is chosen; an explicit MACHE_HOST wins."""
    environment = dict(environ)
    if (app_dir / NETWORK_ACCESS_MARKER).is_file():
        environment.setdefault("MACHE_HOST", "0.0.0.0")
    return environment


def reader_running(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url}api/ports", timeout=PROBE_TIMEOUT_S) as response:
            return isinstance(json.load(response), list)
    except OSError, ValueError:
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
    urls = network_urls(settings)
    if urls:
        print("Other devices on your network can open the reader at one of:")
        for network_url in urls:
            print(f"  {network_url}")
    print("Your browser opens automatically. To stop the reader, close this window or press Ctrl+C.")

    def open_gui() -> None:
        open_url(url)

    serve_gui(settings, open_gui)
    return 0


def main() -> int:
    try:
        settings = Settings.from_env(launch_environment(os.environ, Path(sys.executable).parent))
    except ValueError as exc:
        print(f"Invalid MACHE_* setting: {exc}")
        input("Press Enter to close.")
        return 1
    code = launch(settings, webbrowser.open, serve)
    if code != 0:
        input("Press Enter to close.")
    return code
