"""Certificate routes: issue (staff), verify (public), revoke/restore (staff)."""
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, require_staff
from app.database import get_db
from app.models.certificate import Certificate
from app.models.registration import Registration
from app.models.user import User
from app.models.workshop import Workshop
from app.schemas.certificate import (
    CertificateDetailOut,
    CertificateIssueIn,
    CertificateManualIssueIn,
    CertificateOut,
    CertificateVerifyOut,
)

router = APIRouter(prefix="/api/v1/certificates", tags=["certificates"])


def _gen_cert_id() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "CW-2026-" + "".join(secrets.choice(alphabet) for _ in range(4))


@router.post("/issue", response_model=CertificateOut, status_code=status.HTTP_201_CREATED)
async def issue_certificate(
    data: CertificateIssueIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)
):
    reg = (
        await db.execute(select(Registration).where(Registration.id == data.registration_id))
    ).scalar_one_or_none()
    if reg is None:
        raise HTTPException(status_code=404, detail="Registration not found")
    existing = (
        await db.execute(select(Certificate).where(Certificate.registration_id == reg.id))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Certificate already issued for this registration")
    cert_id = _gen_cert_id()
    cert = Certificate(
        cert_id=cert_id,
        registration_id=reg.id,
        user_id=reg.user_id,
        workshop_id=reg.workshop_id,
        template=data.template,
        qr_data=f"/verify/{cert_id}",
    )
    db.add(cert)
    await db.commit()
    await db.refresh(cert)
    return cert


@router.post("/issue-manual", response_model=CertificateOut, status_code=status.HTTP_201_CREATED)
async def issue_certificate_manual(
    data: CertificateManualIssueIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)
):
    """Issue a certificate for a participant by name/email, creating the user
    and registration records if needed (admin convenience)."""
    ws = (await db.execute(select(Workshop).where(Workshop.id == data.workshop_id))).scalar_one_or_none()
    if ws is None:
        raise HTTPException(status_code=404, detail="Workshop not found")

    participant: User | None = None
    if data.email:
        participant = (
            await db.execute(select(User).where(User.email == data.email.strip().lower()))
        ).scalar_one_or_none()
    if participant is None:
        participant = User(
            email=(data.email.strip().lower() if data.email else f"manual-{secrets.token_hex(4)}@placeholder.local"),
            name=data.name.strip(),
            password_hash="!",
            role="student",
        )
        db.add(participant)
        await db.flush()

    reg = (
        await db.execute(
            select(Registration).where(
                Registration.user_id == participant.id, Registration.workshop_id == ws.id
            )
        )
    ).scalar_one_or_none()
    if reg is None:
        reg = Registration(
            reg_id="WS-2026-" + "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6)),
            user_id=participant.id,
            workshop_id=ws.id,
            status="attended",
        )
        db.add(reg)
        await db.flush()
    else:
        existing_cert = (
            await db.execute(select(Certificate).where(Certificate.registration_id == reg.id))
        ).scalar_one_or_none()
        if existing_cert:
            raise HTTPException(status_code=400, detail="Certificate already issued for this registration")

    cert_id = _gen_cert_id()
    cert = Certificate(
        cert_id=cert_id,
        registration_id=reg.id,
        user_id=participant.id,
        workshop_id=ws.id,
        template=data.template,
        qr_data=f"/verify/{cert_id}",
    )
    db.add(cert)
    await db.commit()
    await db.refresh(cert)
    return cert


@router.get("/verify/{cert_id}", response_model=CertificateVerifyOut)
async def verify_certificate(cert_id: str, db: AsyncSession = Depends(get_db)):
    cert = (await db.execute(select(Certificate).where(Certificate.cert_id == cert_id))).scalar_one_or_none()
    if cert is None:
        return CertificateVerifyOut(valid=False, cert_id=cert_id)
    holder = (await db.execute(select(User).where(User.id == cert.user_id))).scalar_one_or_none()
    ws = (await db.execute(select(Workshop).where(Workshop.id == cert.workshop_id))).scalar_one_or_none()
    return CertificateVerifyOut(
        valid=not cert.revoked,
        cert_id=cert.cert_id,
        holder_name=holder.name if holder else None,
        workshop_title=ws.title if ws else None,
        issued_at=cert.issued_at,
        revoked=cert.revoked,
    )


@router.post("/{cert_id}/revoke", response_model=CertificateOut)
async def revoke_certificate(cert_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)):
    cert = (await db.execute(select(Certificate).where(Certificate.cert_id == cert_id))).scalar_one_or_none()
    if cert is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    cert.revoked = True
    await db.commit()
    await db.refresh(cert)
    return cert


@router.post("/{cert_id}/restore", response_model=CertificateOut)
async def restore_certificate(cert_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)):
    cert = (await db.execute(select(Certificate).where(Certificate.cert_id == cert_id))).scalar_one_or_none()
    if cert is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    cert.revoked = False
    await db.commit()
    await db.refresh(cert)
    return cert


@router.get("/me", response_model=list[CertificateOut])
async def my_certificates(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        await db.execute(
            select(Certificate).where(Certificate.user_id == user.id).order_by(Certificate.issued_at.desc())
        )
    ).scalars().all()
    return rows


@router.get("", response_model=list[CertificateDetailOut])
async def all_certificates(db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)):
    rows = (
        await db.execute(
            select(Certificate, User, Workshop)
            .join(User, Certificate.user_id == User.id)
            .join(Workshop, Certificate.workshop_id == Workshop.id)
            .order_by(Certificate.issued_at.desc())
        )
    ).all()
    out: list[CertificateDetailOut] = []
    for cert, u, w in rows:
        d = CertificateDetailOut.model_validate(cert)
        d.holder_name = u.name
        d.holder_email = u.email
        d.workshop_title = w.title
        out.append(d)
    return out
