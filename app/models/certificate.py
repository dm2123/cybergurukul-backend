"""Certificate model: issued credential for a registration."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cert_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)  # e.g. CW-2026-XXXX
    registration_id: Mapped[int] = mapped_column(ForeignKey("registrations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workshop_id: Mapped[int] = mapped_column(ForeignKey("workshops.id", ondelete="CASCADE"), nullable=False)
    template: Mapped[str] = mapped_column(String(32), default="navy_gold", nullable=False)
    qr_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # verification URL payload
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    registration: Mapped["Registration"] = relationship(back_populates="certificate")
    user: Mapped["User"] = relationship(back_populates="certificates")
    workshop: Mapped["Workshop"] = relationship(back_populates="certificates")
