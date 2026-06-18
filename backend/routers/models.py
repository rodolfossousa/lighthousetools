from fastapi import APIRouter, Depends, HTTPException, Query
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

    results = {"success": 0, "error": 0, "errors": []}
    for gid in body.generator_ids:
        try:
            response = ws.change_generator_status(gid, body.status)
            if hasattr(response, "status_code") and response.status_code in (200, 201, 204):
                results["success"] += 1
            else:
                results["error"] += 1
                results["errors"].append(f"{gid}: HTTP {getattr(response, 'status_code', '?')}")
        except Exception as e:
            results["error"] += 1
            results["errors"].append(f"{gid}: {e}")

    return results
