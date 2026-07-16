import asyncio
import contextlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import admin, auth, files, summary, transactions
from .auth import bootstrap_admin
from .config import settings
from .db import SessionLocal
from .services.retention import retention_loop


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        bootstrap_admin(db)
    finally:
        db.close()

    task = asyncio.create_task(retention_loop())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="Banco - Gestão de Extratos", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(files.router)
app.include_router(transactions.router)
app.include_router(summary.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
