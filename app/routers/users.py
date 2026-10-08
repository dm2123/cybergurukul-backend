"""Public user profile (non-sensitive participant info)."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.certificate import Certificate
from app.models.registration import Registration
from app.models.user import User
from app.models.workshop import Workshop

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
async def public_profile(user_id: int, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    reg_rows = (
        await db.execute(
            select(Registration, Workshop)
            .join(Workshop, Registration.workshop_id == Workshop.id)
            .where(Registration.user_id == user.id, Registration.status != "cancelled")
            .order_by(Registration.registered_at.desc())
        )
    ).all()

    cert_rows = (
        await db.execute(
            select(Certificate, Workshop)
            .join(Workshop, Certificate.workshop_id == Workshop.id)
            .where(Certificate.user_id == user.id, Certificate.revoked == False)  # noqa: E712
            .order_by(Certificate.issued_at.desc())
        )
    ).all()

    return PublicProfileOut(
        id=user.id,
        name=user.name,
        member_since=user.created_at.date().isoformat() if user.created_at else "",
        workshops=[
            ProfileWorkshop(
                title=w.title,
                reg_id=r.reg_id,
                status=r.status,
                registered_at=r.registered_at.date().isoformat() if r.registered_at else "",
            )
            for r, w in reg_rows
        ],
        certificates=[
            ProfileCertificate(
                cert_id=c.cert_id,
                workshop=w.title,
                issued_at=c.issued_at.date().isoformat() if c.issued_at else "",
            )
            for c, w in cert_rows
        ],
    )
