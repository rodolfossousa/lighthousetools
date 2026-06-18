from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from connections import get_environments, connect_environment, get_connection

router = APIRouter()


class ConnectRequest(BaseModel):
    environment: str
    client_name: str


@router.get("")
async def list_environments():
    return get_environments()


@router.post("/connect")
async def connect(body: ConnectRequest, user: dict = Depends(get_current_user)):
    try:
        connect_environment(user["id"], body.environment, body.client_name)
        return {"message": "Conectado.", "environment": body.environment, "client_name": body.client_name}
    except KeyError:
        raise HTTPException(status_code=400, detail="Ambiente ou cliente inválido.")
