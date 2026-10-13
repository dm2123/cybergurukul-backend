"""CyberGurukul enterprise backend — FastAPI application entrypoint.

100% Zoho: data lives in Catalyst Data Store (tables created in the
Project-Rainfall console). No SQLAlchemy, no external database.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, certificates, registrations, stats, users, workshops

app = FastAPI(
    title="CyberGurukul API",
    description="Workshop & Digital Certificate Management Platform — core backend",
    version="0.2.0",
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
app.include_router(stats.router)
app.include_router(users.router)
