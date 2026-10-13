"""Workshop routes: public list/detail + admin CRUD."""
from fastapi import APIRouter, Depends, HTTPException, status

from app import catalyst_db
from app.auth.deps import require_staff
from app.catalyst_db import User, Workshop
from app.schemas.workshop import WorkshopIn, WorkshopOut

router = APIRouter(prefix="/api/v1/workshops", tags=["workshops"])


async def _to_out(w: Workshop) -> WorkshopOut:
    count = await catalyst_db.count_registrations_for_workshop(w.id)
    out = WorkshopOut.model_validate(w)
    out.registered_count = count
    return out


@router.get("", response_model=list[WorkshopOut])
async def list_workshops():
    rows = await catalyst_db.list_workshops()
    return [await _to_out(w) for w in rows]


@router.get("/{slug}", response_model=WorkshopOut)
async def get_workshop(slug: str):
    w = await catalyst_db.get_workshop_by_slug(slug)
    if w is None:
        raise HTTPException(status_code=404, detail="Workshop not found")
    return await _to_out(w)


@router.post("", response_model=WorkshopOut, status_code=status.HTTP_201_CREATED)
async def create_workshop(
    data: WorkshopIn, user: User = Depends(require_staff)
):
    existing = await catalyst_db.get_workshop_by_slug(data.slug)
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists")
    w = await catalyst_db.create_workshop(data.model_dump())
    return await _to_out(w)


@router.put("/{slug}", response_model=WorkshopOut)
async def update_workshop(
    slug: str, data: WorkshopIn, user: User = Depends(require_staff)
):
    w = await catalyst_db.get_workshop_by_slug(slug)
    if w is None:
        raise HTTPException(status_code=404, detail="Workshop not found")
    updated = await catalyst_db.update_workshop(w.id, data.model_dump())
    return await _to_out(updated)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workshop(slug: str, user: User = Depends(require_staff)):
    w = await catalyst_db.get_workshop_by_slug(slug)
    if w is None:
        raise HTTPException(status_code=404, detail="Workshop not found")
    await catalyst_db.delete_workshop(w.id)
