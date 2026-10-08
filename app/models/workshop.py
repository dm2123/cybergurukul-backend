"""Workshop model."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Workshop(Base):
    __tablename__ = "workshops"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(64), default="Cybersecurity", nullable=False)
    date: Mapped[str] = mapped_column(String(32), nullable=False)  # ISO date, e.g. 2026-11-15
    time: Mapped[str] = mapped_column(String(32), nullable=False)  # e.g. 10:00 AM IST
    duration: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    mode: Mapped[str] = mapped_column(String(32), default="Online", nullable=False)
    price: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0 = free
    instructor: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    syllabus: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_seats: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="upcoming", nullable=False)  # upcoming|live|completed|draft
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    registrations: Mapped[list["Registration"]] = relationship(back_populates="workshop", cascade="all, delete-orphan")
    certificates: Mapped[list["Certificate"]] = relationship(back_populates="workshop", cascade="all, delete-orphan")
