"""initial Telegram schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("tg_user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=4), nullable=False, server_default="en"),
        sa.Column("default_zodiac", sa.String(length=16), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("digest_opt_in", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("digest_time", sa.String(length=5), nullable=False, server_default="07:00"),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("tg_user_id"),
    )

    op.create_table(
        "conversation_states",
        sa.Column("tg_user_id", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="idle"),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("tg_user_id"),
    )

    op.create_table(
        "snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("ok", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("etag", sa.String(length=255), nullable=True),
        sa.Column("last_modified", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_snapshots_source", "snapshots", ["source"])
    op.create_index("ix_snapshots_source_fetched", "snapshots", ["source", "fetched_at"])

    op.create_table(
        "telegram_updates",
        sa.Column("update_id", sa.BigInteger(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("update_id"),
    )

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tg_user_id_hash", sa.String(length=64), nullable=False),
        sa.Column("event", sa.String(length=64), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_tg_user_id_hash", "events", ["tg_user_id_hash"])
    op.create_index("ix_events_event", "events", ["event"])
    op.create_index("ix_events_event_ts", "events", ["event", "ts"])

    op.create_table(
        "horoscopes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sign", sa.String(length=16), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("text_en", sa.Text(), nullable=False, server_default=""),
        sa.Column("text_ne", sa.Text(), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sign", "date", name="uq_horoscope_sign_date"),
    )

    op.create_table(
        "source_state",
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("source"),
    )


def downgrade() -> None:
    op.drop_table("source_state")
    op.drop_table("horoscopes")
    op.drop_index("ix_events_event_ts", table_name="events")
    op.drop_index("ix_events_event", table_name="events")
    op.drop_index("ix_events_tg_user_id_hash", table_name="events")
    op.drop_table("events")
    op.drop_table("telegram_updates")
    op.drop_index("ix_snapshots_source_fetched", table_name="snapshots")
    op.drop_index("ix_snapshots_source", table_name="snapshots")
    op.drop_table("snapshots")
    op.drop_table("conversation_states")
    op.drop_table("users")
