"""Public user profile (non-sensitive participant info)."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app import catalyst_db

router = APIRouter(prefix="/api/v1/users", tags=["users"])


class ProfileWorkshop(BaseModel):
    title: str
    reg_id: str
    status: str
    registered_at: str


class ProfileCertificate(BaseModel):
    cert_id: str
    workshop: str
    issued_at: str


class PublicProfileOut(BaseModel):
    id: int
    name: str
    member_since: str
    workshops: list[ProfileWorkshop]
    certificates: list[ProfileCertificate]


@router.get("/{user_id}/profile", response_model=PublicProfileOut)
async def public_profile(user_id: int):
    user = await catalyst_db.get_user_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    reg_rows = await catalyst_db.list_registrations_by_user(user.id)
    cert_rows = await catalyst_db.list_certificates_by_user(user.id)

    workshops = []
    for r in reg_rows:
        if r.status == "cancelled":
            continue
        w = await catalyst_db.get_workshop_by_id(r.workshop_id)
        workshops.append(ProfileWorkshop(
            title=w.title if w else "",
            reg_id=r.reg_id,
            status=r.status,
            registered_at=(r.registered_at[:10] if r.registered_at else ""),
        ))

    certificates = []
    for c in cert_rows:
        if c.revoked:
            continue
        w = await catalyst_db.get_workshop_by_id(c.workshop_id)
        certificates.append(ProfileCertificate(
            cert_id=c.cert_id,
            workshop=w.title if w else "",
            issued_at=(c.issued_at[:10] if c.issued_at else ""),
        ))

    member_since = user.created_at[:10] if user.created_at else ""
    return PublicProfileOut(
        id=user.id,
        name=user.name,
        member_since=member_since,
        workshops=workshops,
        certificates=certificates,
    )
