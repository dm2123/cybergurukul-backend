"""Certificate routes: issue (staff), verify (public), revoke/restore (staff)."""
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, status

from app import catalyst_db
from app.auth.deps import get_current_user, require_staff
from app.catalyst_db import User
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
    data: CertificateIssueIn, user: User = Depends(require_staff)
):
    reg = await catalyst_db.get_registration_by_id(data.registration_id)
    if reg is None:
        raise HTTPException(status_code=404, detail="Registration not found")
    existing = await catalyst_db.get_certificate_by_registration(reg.id)
    if existing:
        raise HTTPException(status_code=400, detail="Certificate already issued for this registration")
    cert_id = _gen_cert_id()
    cert = await catalyst_db.create_certificate(
        cert_id=cert_id,
        registration_id=reg.id,
        user_id=reg.user_id,
        workshop_id=reg.workshop_id,
        template=data.template,
        qr_data=f"/verify/{cert_id}",
    )
    return cert


@router.post("/issue-manual", response_model=CertificateOut, status_code=status.HTTP_201_CREATED)
async def issue_certificate_manual(
    data: CertificateManualIssueIn, user: User = Depends(require_staff)
):
    """Issue a certificate for a participant by name/email, creating the user
    and registration records if needed (admin convenience)."""
    ws = await catalyst_db.get_workshop_by_id(data.workshop_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workshop not found")

    participant = None
    if data.email:
        participant = await catalyst_db.get_user_by_email(data.email.strip().lower())
    if participant is None:
        participant = await catalyst_db.create_user(
            email=(data.email.strip().lower() if data.email else f"manual-{secrets.token_hex(4)}@placeholder.local"),
            name=data.name.strip(),
            password_hash="!",
            role="student",
        )

    reg = await catalyst_db.get_registration_by_user_workshop(participant.id, ws.id)
    if reg is None:
        reg = await catalyst_db.create_registration(
            reg_id="WS-2026-" + "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6)),
            user_id=participant.id,
            workshop_id=ws.id,
            status="attended",
        )
    else:
        existing_cert = await catalyst_db.get_certificate_by_registration(reg.id)
        if existing_cert:
            raise HTTPException(status_code=400, detail="Certificate already issued for this registration")

    cert_id = _gen_cert_id()
    cert = await catalyst_db.create_certificate(
        cert_id=cert_id,
        registration_id=reg.id,
        user_id=participant.id,
        workshop_id=ws.id,
        template=data.template,
        qr_data=f"/verify/{cert_id}",
    )
    return cert


@router.get("/verify/{cert_id}", response_model=CertificateVerifyOut)
async def verify_certificate(cert_id: str):
    cert = await catalyst_db.get_certificate_by_cert_id(cert_id)
    if cert is None:
        return CertificateVerifyOut(valid=False, cert_id=cert_id)
    holder = await catalyst_db.get_user_by_id(cert.user_id)
    ws = await catalyst_db.get_workshop_by_id(cert.workshop_id)
    return CertificateVerifyOut(
        valid=not cert.revoked,
        cert_id=cert.cert_id,
        holder_name=holder.name if holder else None,
        workshop_title=ws.title if ws else None,
        issued_at=cert.issued_at,
        revoked=cert.revoked,
    )


@router.post("/{cert_id}/revoke", response_model=CertificateOut)
async def revoke_certificate(cert_id: str, user: User = Depends(require_staff)):
    cert = await catalyst_db.get_certificate_by_cert_id(cert_id)
    if cert is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return await catalyst_db.set_certificate_revoked(cert.id, True)


@router.post("/{cert_id}/restore", response_model=CertificateOut)
async def restore_certificate(cert_id: str, user: User = Depends(require_staff)):
    cert = await catalyst_db.get_certificate_by_cert_id(cert_id)
    if cert is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return await catalyst_db.set_certificate_revoked(cert.id, False)


@router.get("/me", response_model=list[CertificateOut])
async def my_certificates(user: User = Depends(get_current_user)):
    return await catalyst_db.list_certificates_by_user(user.id)


@router.get("", response_model=list[CertificateDetailOut])
async def all_certificates(user: User = Depends(require_staff)):
    rows = await catalyst_db.list_all_certificates()
    out: list[CertificateDetailOut] = []
    for cert in rows:
        d = CertificateDetailOut.model_validate(cert)
        u = await catalyst_db.get_user_by_id(cert.user_id)
        w = await catalyst_db.get_workshop_by_id(cert.workshop_id)
        d.holder_name = u.name if u else ""
        d.holder_email = u.email if u else ""
        d.workshop_title = w.title if w else ""
        out.append(d)
    return out
