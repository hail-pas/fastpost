from fastapi import FastAPI

from apps.websocket.routes.hello import func_websocket_route
from apps.websocket.routes.ticks import WebSocketTicks

ws_app = FastAPI()

ws_app.add_api_websocket_route("/example", func_websocket_route, "hello")
ws_app.add_websocket_route("/example2", WebSocketTicks, "Tick")
