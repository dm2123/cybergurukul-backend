"""CyberGurukul enterprise backend — FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401 — register models for Base.metadata
from app.config import settings
from app.routers import auth, certificates, registrations, workshops


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tables are created via Alembic migrations in production.
    # Uncomment for quick local bootstrap:
    # from app.database import init_db
    # await init_db()
    yield


app = FastAPI(
    title="CyberGurukul API",
    description="Workshop & Digital Certificate Management Platform — core backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": "cybergurukul-api"}


app.include_router(auth.router)
app.include_router(workshops.router)
app.include_router(registrations.router)
app.include_router(certificates.router)
