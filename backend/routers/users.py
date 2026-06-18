from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from db import list_users, create_user, delete_user, reset_password
from auth import require_admin

router = APIRouter()


class CreateUserRequest(BaseModel):
    username: str
    password: str
    name: str
    is_admin: bool = False


class ResetPasswordRequest(BaseModel):
    new_password: str


@router.get("")
async def get_users(_: dict = Depends(require_admin)):
    return list_users()


@router.post("")
async def post_user(body: CreateUserRequest, _: dict = Depends(require_admin)):
    if not body.username or not body.password or not body.name:
        raise HTTPException(status_code=400, detail="Preenche todos os campos.")
    ok = create_user(body.username, body.password, body.name, body.is_admin)
    if not ok:
        raise HTTPException(status_code=409, detail=f"Username '{body.username}' já existe.")
    return {"message": "Utilizador criado."}


@router.delete("/{user_id}")
async def remove_user(user_id: int, _: dict = Depends(require_admin)):
    ok = delete_user(user_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Não foi possível remover o utilizador.")
    return {"message": "Utilizador removido."}


@router.patch("/{user_id}/password")
async def patch_password(user_id: int, body: ResetPasswordRequest, _: dict = Depends(require_admin)):
    if not body.new_password:
        raise HTTPException(status_code=400, detail="Informa a nova senha.")
    reset_password(user_id, body.new_password)
    return {"message": "Senha atualizada."}
