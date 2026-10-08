"""Certificate request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, Field


class CertificateIssueIn(BaseModel):
    registration_id: int
    template: str = Field(default="navy_gold", max_length=32)


class CertificateManualIssueIn(BaseModel):
    workshop_id: int
    name: str = Field(min_length=2, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    template: str = Field(default="navy_gold", max_length=32)


class CertificateOut(BaseModel):
    id: int
    cert_id: str
    registration_id: int
    user_id: int
    workshop_id: int
    template: str
    qr_data: str | None
    revoked: bool
    issued_at: datetime

    model_config = {"from_attributes": True}


class CertificateVerifyOut(BaseModel):
    valid: bool
    cert_id: str
    holder_name: str | None = None
    workshop_title: str | None = None
    issued_at: datetime | None = None
    revoked: bool = False
