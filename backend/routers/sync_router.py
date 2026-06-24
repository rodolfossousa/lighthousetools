import json
import queue
import threading

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
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


def _sse_sync(sync_fn, done_label: str):
    q: queue.Queue = queue.Queue()

    def progress(current, total, name):
        q.put({"current": current, "total": total, "name": name})

    def run():
        try:
            total = sync_fn(progress_callback=progress)
            q.put({"done": True, "total": total, "message": f"Sincronização concluída: {total} {done_label}."})
        except Exception as e:
            q.put({"error": str(e)})

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    def event_stream():
        while True:
            try:
                msg = q.get(timeout=600)
            except queue.Empty:
                yield f"data: {json.dumps({'error': 'Timeout interno.'})}\n\n"
                break
            yield f"data: {json.dumps(msg)}\n\n"
            if "done" in msg or "error" in msg:
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/items")
async def do_sync_items(body: SyncItemsRequest, user: dict = Depends(get_current_user)):
    ws = get_connection(user["id"], body.environment, body.client_name)
    if not ws:
        raise HTTPException(status_code=400, detail="Ambiente não conectado.")

    def sync_fn(progress_callback):
        return sync_items(ws, body.root_id, body.vessel_name, body.environment, body.client_name, progress_callback=progress_callback)

    return _sse_sync(sync_fn, "registros salvos")


@router.post("/templates")
async def do_sync_templates(body: SyncTemplatesRequest, user: dict = Depends(get_current_user)):
    ws = get_connection(user["id"], body.environment, body.client_name)
    if not ws:
        raise HTTPException(status_code=400, detail="Ambiente não conectado.")

    def sync_fn(progress_callback):
        return sync_templates(ws, body.environment, body.client_name, template_ids=body.template_ids, progress_callback=progress_callback)

    return _sse_sync(sync_fn, "atributos salvos")


@router.get("/templates/list")
async def list_available_templates(
    environment: str, client_name: str,
    user: dict = Depends(get_current_user),
):
    ws = get_connection(user["id"], environment, client_name)
    if not ws:
        raise HTTPException(status_code=400, detail="Ambiente não conectado.")
    return ws.get_templates()
