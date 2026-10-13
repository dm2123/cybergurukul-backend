"""Public platform statistics (for the homepage counters)."""
from fastapi import APIRouter
from pydantic import BaseModel

from app import catalyst_db

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


class StatsOut(BaseModel):
    workshops: int
    registrations: int
    certificates: int


@router.get("", response_model=StatsOut)
async def public_stats():
    w = await catalyst_db.count_workshops_active()
    r = await catalyst_db.count_registrations()
    c = await catalyst_db.count_certificates_valid()
    return StatsOut(workshops=w, registrations=r, certificates=c)
