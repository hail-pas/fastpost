import asyncio
import logging
from typing import Any

from fastapi import FastAPI, WebSocket
from starlette.endpoints import WebSocketEndpoint
from starlette.websockets import WebSocketDisconnect

from apps.spi.manage import ws_manager

logger = logging.getLogger("websocket")

spi_app = FastAPI()


@spi_app.websocket("/example")
async def func_websocket_route(websocket: WebSocket, client_id: int):
    await ws_manager.connect(websocket)
    try:
        await ws_manager.send_privete_json({"msg": "Hello WebSocket"}, websocket)
        while True:
            data = await websocket.receive_text()
            await ws_manager.send_private_message(f"You wrote: {data}", websocket)
            await ws_manager.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        await ws_manager.broadcast(f"Client #{client_id} left the chat")


class WebSocketTicks(WebSocketEndpoint):
    encoding = "json"

    async def on_connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.ticker_task = asyncio.create_task(self.tick(websocket))
        logger.info(
            '%s - "WebSocket %s" [accepted]',
            websocket.scope["client"],
            websocket.scope["root_path"] + websocket.scope["path"],
        )

    async def on_disconnect(self, websocket: WebSocket, close_code: int) -> None:
        self.ticker_task.cancel()
        logger.info(
            '%s - "WebSocket %s" [disconnected]',
            websocket.scope["client"],
            websocket.scope["root_path"] + websocket.scope["path"],
        )

    async def on_receive(self, websocket: WebSocket, data: Any) -> None:
        await websocket.send_json({"Message: ": data})

    async def tick(self, websocket: WebSocket) -> None:
        counter = 0
        while True:
            logger.info(counter)
            await websocket.send_json({"counter": counter})
            counter += 1
            await asyncio.sleep(1)


spi_app.add_websocket_route("/example2", WebSocketTicks, "Tick")
