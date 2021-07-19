from fastapi import Depends, APIRouter

from core.schema import Pager
from core.globals import g
from core.response import PageResp
from db.mysql.models import Address
from apps.dependencies import get_pager

router = APIRouter()


@router.get("/address", summary="地址", description="地址", response_model=PageResp[Address.response_model])
async def get_address(pager: Pager = Depends(get_pager)):
    page_info, data = await Address.page_data(pager=pager, user_id=g.user.id)
    return PageResp[Address.response_model](page_info=page_info, data=data)
