from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from fastpost.globals import g
from fastpost.response import Resp

router = APIRouter(prefix="/user")


class Address(BaseModel):
    province: str
    city: str
    detail: Optional[str]


@router.post("/address", summary="地址", description="地址", response_model=Resp[List[Address]])
async def get_address():
    print(g.user)
    return Resp[List[Address]](data=[{"province": "重庆市", "city": "江北区", "detail": None}])
