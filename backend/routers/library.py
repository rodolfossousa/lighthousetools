from fastapi import APIRouter, Depends

from auth import get_current_user
from db_lighthouse import get_template_list, get_template_attr_tree

router = APIRouter()


@router.get("/templates")
async def list_templates(
    environment: str, client_name: str,
    _: dict = Depends(get_current_user),
):
    return get_template_list(environment, client_name)


@router.get("/templates/{template_id}/tree")
async def template_tree(
    template_id: str, environment: str, client_name: str,
    _: dict = Depends(get_current_user),
):
    return get_template_attr_tree(environment, client_name, template_id)
