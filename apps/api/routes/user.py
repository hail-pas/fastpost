from fastapi import APIRouter, Depends

from apps.depends import get_pager
from db.models import Address
from fastpost.globals import g
from fastpost.response import PageResp
from fastpost.types import Pager

router = APIRouter(prefix="/user")


@router.post("/address", summary="地址", description="地址", response_model=PageResp[Address.response_model])
async def get_address(pager: Pager = Depends(get_pager)):
    page_info, data = await Address.page_data(pager=pager, user_id=g.user.id)
    return PageResp[Address.response_model](page_info=page_info, data=data)
