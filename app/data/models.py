"""SQLAlchemy ORM models. Kept intentionally small: no data beyond what a reply needs.

Users are keyed by ``tg_user_id`` (the numeric Telegram id). It is far less sensitive than a
phone number, but it is still never logged (analytics store a salted hash) and preference
data is purged after opt-out.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db import Base

# JSONB on Postgres, plain JSON elsewhere (SQLite).
JSONType = JSON().with_variant(JSONB, "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    #: Numeric Telegram user id (= chat id in private chats).
    tg_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(4), default="en", nullable=False)
    default_zodiac: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    digest_opt_in: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    daily_briefing_opt_out: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    digest_time: Mapped[str] = mapped_column(String(5), default="07:00", nullable=False)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ConversationState(Base):
    __tablename__ = "conversation_states"

    tg_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    state: Mapped[str] = mapped_column(String(32), default="idle", nullable=False)
    context: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Snapshot(Base):
    """A frozen copy of a source payload, so we never scrape on a user tap."""

    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_modified: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (Index("ix_snapshots_source_fetched", "source", "fetched_at"),)


class UpdateRecord(Base):
    """Dedupe store for inbound updates (webhook retries / polling replays)."""

    __tablename__ = "telegram_updates"

    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Event(Base):
    """Privacy-friendly analytics: only a salted hash of the Telegram id is stored."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_user_id_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (Index("ix_events_event_ts", "event", "ts"),)


class Horoscope(Base):
    __tablename__ = "horoscopes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sign: Mapped[str] = mapped_column(String(16), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    text_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    text_ne: Mapped[str] = mapped_column(Text, nullable=False, default="")

    __table_args__ = (UniqueConstraint("sign", "date", name="uq_horoscope_sign_date"),)


class SourceState(Base):
    """Scheduler bookkeeping for each source."""

    __tablename__ = "source_state"

    source: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
