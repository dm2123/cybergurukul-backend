"""Public platform statistics (for the homepage counters)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.certificate import Certificate
from app.models.registration import Registration
from app.models.workshop import Workshop

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


class StatsOut(BaseModel):
    workshops: int
    registrations: int
    certificates: int


@router.get("", response_model=StatsOut)
async def public_stats(db: AsyncSession = Depends(get_db)):
    w = (await db.execute(select(func.count()).where(Workshop.status != "draft"))).scalar() or 0
    r = (await db.execute(select(func.count()).select_from(Registration))).scalar() or 0
    c = (
        await db.execute(select(func.count()).where(Certificate.revoked == False))  # noqa: E712
    ).scalar() or 0
    return StatsOut(workshops=w, registrations=r, certificates=c)
