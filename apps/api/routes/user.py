from fastapi import Depends, APIRouter

from db.mysql.models import Address
from fastpost.schema import Pager
from fastpost.globals import g
from apps.dependencies import get_pager
from fastpost.response import PageResp

router = APIRouter()


@router.get("/address", summary="地址", description="地址", response_model=PageResp[Address.response_model])
async def get_address(pager: Pager = Depends(get_pager)):
    page_info, data = await Address.page_data(pager=pager, user_id=g.user.id)
    return PageResp[Address.response_model](page_info=page_info, data=data)
