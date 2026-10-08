"""Workshop routes: public list/detail + admin CRUD."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_staff
from app.database import get_db
from app.models.registration import Registration
from app.models.user import User
from app.models.workshop import Workshop
from app.schemas.workshop import WorkshopIn, WorkshopOut

router = APIRouter(prefix="/api/v1/workshops", tags=["workshops"])


async def _to_out(db: AsyncSession, w: Workshop) -> WorkshopOut:
    count = (
        await db.execute(select(func.count()).where(Registration.workshop_id == w.id))
    ).scalar() or 0
    out = WorkshopOut.model_validate(w)
    out.registered_count = count
    return out


@router.get("", response_model=list[WorkshopOut])
async def list_workshops(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Workshop).order_by(Workshop.date))).scalars().all()
    return [await _to_out(db, w) for w in rows]


@router.get("/{slug}", response_model=WorkshopOut)
async def get_workshop(slug: str, db: AsyncSession = Depends(get_db)):
    w = (await db.execute(select(Workshop).where(Workshop.slug == slug))).scalar_one_or_none()
    if w is None:
        raise HTTPException(status_code=404, detail="Workshop not found")
    return await _to_out(db, w)


@router.post("", response_model=WorkshopOut, status_code=status.HTTP_201_CREATED)
async def create_workshop(
    data: WorkshopIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)
):
    existing = (await db.execute(select(Workshop).where(Workshop.slug == data.slug))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists")
    w = Workshop(**data.model_dump())
    db.add(w)
    await db.commit()
    await db.refresh(w)
    return await _to_out(db, w)


@router.put("/{slug}", response_model=WorkshopOut)
async def update_workshop(
    slug: str, data: WorkshopIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)
):
    w = (await db.execute(select(Workshop).where(Workshop.slug == slug))).scalar_one_or_none()
    if w is None:
        raise HTTPException(status_code=404, detail="Workshop not found")
    for k, v in data.model_dump().items():
        setattr(w, k, v)
    await db.commit()
    await db.refresh(w)
    return await _to_out(db, w)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workshop(slug: str, db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)):
    w = (await db.execute(select(Workshop).where(Workshop.slug == slug))).scalar_one_or_none()
    if w is None:
        raise HTTPException(status_code=404, detail="Workshop not found")
    await db.delete(w)
    await db.commit()
