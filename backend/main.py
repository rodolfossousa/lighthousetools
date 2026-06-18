import sys
from pathlib import Path

# Adiciona app/ ao path para reutilizar db.py, db_lighthouse.py, sync.py
sys.path.append(str(Path(__file__).resolve().parent.parent / "app"))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import init_db
from db_lighthouse import init_lighthouse_db

from routers import auth_router, users, environments, explorer, models, sync_router, dictionary, templates, library


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_lighthouse_db()
    yield


app = FastAPI(title="Lighthouse Tools API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/api/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(environments.router, prefix="/api/environments", tags=["Environments"])
app.include_router(explorer.router, prefix="/api/explorer", tags=["Explorer"])
app.include_router(models.router, prefix="/api/models", tags=["Models"])
app.include_router(sync_router.router, prefix="/api/sync", tags=["Sync"])
app.include_router(dictionary.router, prefix="/api/dictionary", tags=["Dictionary"])
app.include_router(templates.router, prefix="/api/templates", tags=["Templates"])
app.include_router(library.router, prefix="/api/library", tags=["Library"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.1"}
