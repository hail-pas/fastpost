"""
Websocket
"""


from socketio import ASGIApp, AsyncServer, AsyncRedisManager

from fastpost.settings import settings

sio = AsyncServer(
    client_manager=AsyncRedisManager(settings.SIO_REDIS_URL), async_mode="asgi", cors_allowed_origins=["*"],
)

spi_app = ASGIApp(socketio_server=sio, socketio_path="/socket.io")


@sio.on("connect")
async def on_connect(sid, environ, auth):
    # await sio.emit("drawing", kwargs)
    ...


@sio.on("drawing")
async def on_drawing(sid, data):
    await sio.emit("drawing", data, broadcast=True)
