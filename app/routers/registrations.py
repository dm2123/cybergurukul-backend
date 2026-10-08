"""Registration routes: register for a workshop, list own registrations, admin list."""
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, require_staff
from app.database import get_db
from app.models.registration import Registration
from app.models.user import User
from app.models.workshop import Workshop
from app.schemas.registration import (
    RegistrationDetailOut,
    RegistrationOut,
    RegistrationStatusIn,
)

router = APIRouter(prefix="/api/v1/registrations", tags=["registrations"])


def _gen_reg_id() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "WS-2026-" + "".join(secrets.choice(alphabet) for _ in range(6))


@router.post("/{workshop_slug}", response_model=RegistrationOut, status_code=status.HTTP_201_CREATED)
async def register(
    workshop_slug: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    w = (await db.execute(select(Workshop).where(Workshop.slug == workshop_slug))).scalar_one_or_none()
    if w is None:
        raise HTTPException(status_code=404, detail="Workshop not found")
    if w.status == "completed":
        raise HTTPException(status_code=400, detail="Workshop already completed")
    existing = (
        await db.execute(
            select(Registration).where(
                Registration.user_id == user.id, Registration.workshop_id == w.id
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Already registered for this workshop")
    reg = Registration(reg_id=_gen_reg_id(), user_id=user.id, workshop_id=w.id)
    db.add(reg)
    await db.commit()
    await db.refresh(reg)
    return reg


@router.get("/me", response_model=list[RegistrationOut])
async def my_registrations(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        await db.execute(
            select(Registration).where(Registration.user_id == user.id).order_by(Registration.registered_at.desc())
        )
    ).scalars().all()
    return rows


@router.get("", response_model=list[RegistrationDetailOut])
async def all_registrations(db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)):
    rows = (
        await db.execute(
            select(Registration, User, Workshop)
            .join(User, Registration.user_id == User.id)
            .join(Workshop, Registration.workshop_id == Workshop.id)
            .order_by(Registration.registered_at.desc())
        )
    ).all()
    out: list[RegistrationDetailOut] = []
    for reg, u, w in rows:
        d = RegistrationDetailOut.model_validate(reg)
        d.user_name = u.name
        d.user_email = u.email
        d.workshop_title = w.title
        out.append(d)
    return out


@router.patch("/{reg_id}", response_model=RegistrationOut)
async def update_registration_status(
    reg_id: int, data: RegistrationStatusIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)
):
    if data.status not in ("registered", "attended", "cancelled"):
        raise HTTPException(status_code=400, detail="Invalid status")
    reg = (await db.execute(select(Registration).where(Registration.id == reg_id))).scalar_one_or_none()
    if reg is None:
        raise HTTPException(status_code=404, detail="Registration not found")
    reg.status = data.status
    await db.commit()
    await db.refresh(reg)
    return reg


@router.delete("/{reg_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_registration(
    reg_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)
):
    reg = (await db.execute(select(Registration).where(Registration.id == reg_id))).scalar_one_or_none()
    if reg is None:
        raise HTTPException(status_code=404, detail="Registration not found")
    await db.delete(reg)
    await db.commit()
