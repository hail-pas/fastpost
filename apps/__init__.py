from typing import List, Union

from fastapi import FastAPI

from apps.api import api_router
from apps.spi import spi_app

roster: List[List[Union[FastAPI, str]]] = [
    [spi_app, "/ws", "Socket IO"],
    [api_router, "", "API"],
]
