from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from mache_cells.config import Settings
from mache_cells.service import CellMonitor, RequestError, TransportFactory
from mache_cells.transport import SerialTransport

WEB_DIR = Path(__file__).parent / "web"


class ConnectionRequest(BaseModel):
    port: str


def create_app(settings: Settings, open_transport: TransportFactory = SerialTransport) -> FastAPI:
    monitor = CellMonitor(settings, open_transport)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await monitor.disconnect()

    app = FastAPI(title="Mach-E Cell Voltages", lifespan=lifespan)

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

    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app
