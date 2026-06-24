import json
import queue
import threading

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from auth import get_current_user
from connections import get_connection
from db_lighthouse import get_vessels, get_generators

router = APIRouter()


class ChangeStatusRequest(BaseModel):
    generator_ids: list[str]
    status: str
    environment: str
    client_name: str


@router.get("/vessels")
async def list_vessels(_: dict = Depends(get_current_user)):
    return get_vessels()


@router.get("")
async def list_generators(
    vessel: str = Query(None),
    search: str = Query(None),
    _: dict = Depends(get_current_user),
):
    return get_generators(vessel=vessel, search=search)


@router.post("/status")
async def change_status(body: ChangeStatusRequest, user: dict = Depends(get_current_user)):
    if body.status not in ("ONLINE", "OFFLINE"):
        raise HTTPException(status_code=400, detail="Status deve ser ONLINE ou OFFLINE.")
    ws = get_connection(user["id"], body.environment, body.client_name)
    if not ws:
        raise HTTPException(status_code=400, detail="Ambiente não conectado.")

    q: queue.Queue = queue.Queue()
    total = len(body.generator_ids)

    def run():
        success = 0
        errors = []
        for i, gid in enumerate(body.generator_ids):
            try:
                response = ws.change_generator_status(gid, body.status)
                status_code = getattr(response, "status_code", None)
                resp_text = getattr(response, "text", "")
                if status_code and status_code in (200, 201, 204):
                    success += 1
                else:
                    detail = ""
                    try:
                        detail = json.loads(resp_text).get("detail", resp_text[:100])
                    except Exception:
                        detail = resp_text[:100]
                    errors.append(detail)
                    if status_code == 403:
                        q.put({"error": f"Sem permissão de escrita: {detail}"})
                        return
            except Exception as e:
                errors.append(str(e))
            q.put({"current": i + 1, "total": total, "name": f"{i + 1}/{total}"})
        msg = f"{success} modelo(s) alterado(s) para {body.status}."
        if errors:
            msg += f" {len(errors)} erro(s)."
        q.put({"done": True, "total": total, "message": msg, "success": success, "error_count": len(errors), "errors": errors[:5]})

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    def event_stream():
        while True:
            try:
                msg = q.get(timeout=300)
            except queue.Empty:
                yield f"data: {json.dumps({'error': 'Timeout interno.'})}\n\n"
                break
            yield f"data: {json.dumps(msg)}\n\n"
            if "done" in msg or "error" in msg:
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")
