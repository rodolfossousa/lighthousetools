from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from db import authenticate
from auth import create_access_token, get_current_user

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(body: LoginRequest):
    user = authenticate(body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Utilizador ou senha incorretos.")
    token = create_access_token({
        "sub": str(user["id"]),
        "username": user["username"],
        "name": user["name"],
        "is_admin": user["is_admin"],
    })
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user
