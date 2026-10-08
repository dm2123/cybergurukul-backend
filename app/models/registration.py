"""Registration model: a user registered for a workshop."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Registration(Base):
    __tablename__ = "registrations"
    __table_args__ = (UniqueConstraint("user_id", "workshop_id", name="uq_user_workshop"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    reg_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)  # e.g. WS-2026-XXXXXX
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workshop_id: Mapped[int] = mapped_column(ForeignKey("workshops.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="registered", nullable=False)  # registered|attended|cancelled
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="registrations")
    workshop: Mapped["Workshop"] = relationship(back_populates="registrations")
    certificate: Mapped["Certificate | None"] = relationship(back_populates="registration", uselist=False)
