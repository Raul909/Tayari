"""
SQLAlchemy ORM models — the durable, database-backed side of Tayari.

These mirror the Pydantic API schemas in ``schemas.py`` but represent rows in
the shared database (Neon Postgres in production, SQLite locally). The routers
convert between the two so the HTTP contract the web and mobile apps depend on
never changes.
"""

from datetime import datetime

from sqlalchemy import (
    DateTime, Float, ForeignKey, Integer, String, Text, func, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ReportORM(Base):
    """A geotagged community field report."""

    __tablename__ = "community_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    basin_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reporter_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )

    advice: Mapped[list["AdviceORM"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="AdviceORM.created_at",
        lazy="selectin",  # eager-load advice threads without N+1 queries
    )


class AdviceORM(Base):
    """A piece of advice attached to a community report."""

    __tablename__ = "report_advice"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("community_reports.id", ondelete="CASCADE"), index=True,
    )
    message: Mapped[str] = mapped_column(Text)
    author_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    author_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )

    report: Mapped["ReportORM"] = relationship(back_populates="advice")


class AlertORM(Base):
    """A record of an SMS alert that was sent."""

    __tablename__ = "alert_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    basin_id: Mapped[str] = mapped_column(String(64), index=True)
    risk_level: Mapped[str] = mapped_column(String(16))
    role: Mapped[str] = mapped_column(String(32))
    language: Mapped[str] = mapped_column(String(8))
    recipients_count: Mapped[int] = mapped_column(Integer, default=0)
    advisory_text: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )


class UserProfileORM(Base):
    """User profile data linked to Supabase Auth UUID."""

    __tablename__ = "user_profiles"

    # Supabase uses UUIDs for auth.users.id, which we store as a 36-char string.
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    preferred_role: Mapped[str] = mapped_column(String(32), default="general")
    preferred_language: Mapped[str] = mapped_column(String(8), default="en")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )

    saved_basins: Mapped[list["SavedBasinORM"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    prefs: Mapped["UserPrefsORM"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False, lazy="joined"
    )


class SavedBasinORM(Base):
    """A basin bookmarked by a user."""

    __tablename__ = "saved_basins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"), index=True)
    basin_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )

    user: Mapped["UserProfileORM"] = relationship(back_populates="saved_basins")

    __table_args__ = (
        UniqueConstraint("user_id", "basin_id", name="uq_user_basin"),
    )


class UserPrefsORM(Base):
    """Notification preferences for a user."""

    __tablename__ = "user_prefs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"), unique=True, index=True)
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sms_language: Mapped[str] = mapped_column(String(8), default="en")
    sms_role: Mapped[str] = mapped_column(String(32), default="general")
    notify_risk_level: Mapped[str] = mapped_column(String(16), default="HIGH")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["UserProfileORM"] = relationship(back_populates="prefs")
