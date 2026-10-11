import contextlib
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import anyio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.trustedhost import TrustedHostMiddleware

from mache_cells.config import Settings
from mache_cells.network import listens_on_all_interfaces, local_hosts
from mache_cells.service import CellMonitor, RequestError, TransportFactory
from mache_cells.transport import SerialTransport

WEB_DIR = Path(__file__).parent / "web"
LOOPBACK_HOSTS = ("localhost", "127.0.0.1", "[::1]")


class ConnectionRequest(BaseModel):
    port: str


def _is_cross_origin(socket: WebSocket) -> bool:
    """Browsers send Origin on a WebSocket handshake; clients without one are not browser pages."""
    origin = socket.headers.get("origin")
    return origin is not None and urlsplit(origin).netloc.lower() != socket.headers.get("host", "").lower()


async def _push_states(socket: WebSocket, monitor: CellMonitor) -> None:
    """Send every state until the client goes away; a client can leave in the middle of a send."""
    with contextlib.suppress(WebSocketDisconnect):
        async for state in monitor.updates():
            await socket.send_json(state)


async def _until_closed(socket: WebSocket) -> None:
    async for _ in socket.iter_text():
        pass


def create_app(settings: Settings, open_transport: TransportFactory = SerialTransport) -> FastAPI:
    monitor = CellMonitor(settings, open_transport)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await monitor.disconnect()

    app = FastAPI(title="Mach-E Cell Voltages", lifespan=lifespan)
    own_hosts = local_hosts() if listens_on_all_interfaces(settings.host) else ()
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=[*LOOPBACK_HOSTS, *settings.allowed_hosts, *own_hosts]
    )

    async def guarded(action: Awaitable[None]) -> dict[str, Any]:
        try:
            await action
        except RequestError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return monitor.state

    @app.get("/api/ports")
    async def get_ports() -> list[str]:
        return monitor.available_ports()

    @app.get("/api/state")
    async def get_state() -> dict[str, Any]:
        return monitor.state

    @app.put("/api/connection")
    async def put_connection(request: ConnectionRequest) -> dict[str, Any]:
        return await guarded(monitor.connect(request.port))

    @app.delete("/api/connection")
    async def delete_connection() -> dict[str, Any]:
        return await guarded(monitor.disconnect())

    @app.websocket("/api/events")
    async def events(socket: WebSocket) -> None:
        if _is_cross_origin(socket):
            await socket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        await socket.accept()
        async with anyio.create_task_group() as tasks:
            tasks.start_soon(_push_states, socket, monitor)
            await _until_closed(socket)
            tasks.cancel_scope.cancel()

    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app
