from typing import List, Union

from fastapi import FastAPI

from apps.api import api_router
from apps.websocket import ws_app

roster: List[List[Union[FastAPI, str]]] = [
    [ws_app, "/ws", "Socket IO"],
    [api_router, "", "API"],
]
