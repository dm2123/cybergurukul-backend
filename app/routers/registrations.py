"""Registration routes: register for a workshop, list own registrations, admin list."""
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, status

from app import catalyst_db
from app.auth.deps import get_current_user, require_staff
from app.catalyst_db import Registration, User
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
    workshop_slug: str, user: User = Depends(get_current_user)
):
    w = await catalyst_db.get_workshop_by_slug(workshop_slug)
    if w is None:
        raise HTTPException(status_code=404, detail="Workshop not found")
    if w.status == "completed":
        raise HTTPException(status_code=400, detail="Workshop already completed")
    existing = await catalyst_db.get_registration_by_user_workshop(user.id, w.id)
    if existing:
        raise HTTPException(status_code=400, detail="Already registered for this workshop")
    reg = await catalyst_db.create_registration(
        reg_id=_gen_reg_id(), user_id=user.id, workshop_id=w.id
    )
    return reg


@router.get("/me", response_model=list[RegistrationOut])
async def my_registrations(user: User = Depends(get_current_user)):
    return await catalyst_db.list_registrations_by_user(user.id)


@router.get("", response_model=list[RegistrationDetailOut])
async def all_registrations(user: User = Depends(require_staff)):
    rows = await catalyst_db.list_all_registrations()
    out: list[RegistrationDetailOut] = []
    for reg in rows:
        d = RegistrationDetailOut.model_validate(reg)
        u = await catalyst_db.get_user_by_id(reg.user_id)
        w = await catalyst_db.get_workshop_by_id(reg.workshop_id)
        d.user_name = u.name if u else ""
        d.user_email = u.email if u else ""
        d.workshop_title = w.title if w else ""
        out.append(d)
    return out


@router.patch("/{reg_id}", response_model=RegistrationOut)
async def update_registration_status(
    reg_id: int, data: RegistrationStatusIn, user: User = Depends(require_staff)
):
    if data.status not in ("registered", "attended", "cancelled"):
        raise HTTPException(status_code=400, detail="Invalid status")
    reg = await catalyst_db.get_registration_by_id(reg_id)
    if reg is None:
        raise HTTPException(status_code=404, detail="Registration not found")
    return await catalyst_db.update_registration_status(reg_id, data.status)


@router.delete("/{reg_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_registration(
    reg_id: int, user: User = Depends(require_staff)
):
    reg = await catalyst_db.get_registration_by_id(reg_id)
    if reg is None:
        raise HTTPException(status_code=404, detail="Registration not found")
    await catalyst_db.delete_registration(reg_id)
