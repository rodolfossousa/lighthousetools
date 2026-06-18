from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from connections import get_connection
from db_lighthouse import get_sync_history, get_template_list
from sync import find_root_candidates, sync_items, sync_templates

router = APIRouter()


class SyncItemsRequest(BaseModel):
    root_id: str
    vessel_name: str
    environment: str
    client_name: str


class SyncTemplatesRequest(BaseModel):
    environment: str
    client_name: str
    template_ids: list[str] | None = None


class SearchRootRequest(BaseModel):
    search_term: str
    environment: str
    client_name: str


@router.get("/history")
async def history(_: dict = Depends(get_current_user)):
    return get_sync_history()


@router.post("/search-root")
async def search_root(body: SearchRootRequest, user: dict = Depends(get_current_user)):
    ws = get_connection(user["id"], body.environment, body.client_name)
    if not ws:
        raise HTTPException(status_code=400, detail="Ambiente não conectado.")
    candidates = find_root_candidates(ws, body.search_term)
    return [{"id": c[0], "name": c[1]} for c in candidates]


@router.post("/items")
async def do_sync_items(body: SyncItemsRequest, user: dict = Depends(get_current_user)):
    ws = get_connection(user["id"], body.environment, body.client_name)
    if not ws:
        raise HTTPException(status_code=400, detail="Ambiente não conectado.")
    total = sync_items(ws, body.root_id, body.vessel_name, body.environment, body.client_name)
    return {"message": f"Sincronização concluída: {total} registros salvos.", "total": total}


@router.post("/templates")
async def do_sync_templates(body: SyncTemplatesRequest, user: dict = Depends(get_current_user)):
    ws = get_connection(user["id"], body.environment, body.client_name)
    if not ws:
        raise HTTPException(status_code=400, detail="Ambiente não conectado.")
    total = sync_templates(ws, body.environment, body.client_name, template_ids=body.template_ids)
    return {"message": f"Sincronização concluída: {total} atributos salvos.", "total": total}


@router.get("/templates/list")
async def list_available_templates(
    environment: str, client_name: str,
    user: dict = Depends(get_current_user),
):
    ws = get_connection(user["id"], environment, client_name)
    if not ws:
        raise HTTPException(status_code=400, detail="Ambiente não conectado.")
    return ws.get_templates()
