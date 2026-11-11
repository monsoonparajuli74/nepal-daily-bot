"""Analytics events v2: HMAC user hash plus module/lang/source columns.

The user-hash algorithm changed (HMAC-SHA256 over a plain salted digest), so existing
rows can no longer be attributed to anyone: the table is dropped and recreated with the
new schema.

Revision ID: 0003_analytics_events
Revises: 0002_daily_briefing_opt_out
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_analytics_events"
down_revision = "0002_daily_briefing_opt_out"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS events")
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_hash", sa.String(length=64), nullable=False),
        sa.Column("event", sa.String(length=32), nullable=False),
        sa.Column("module", sa.String(length=32), nullable=True),
        sa.Column("lang", sa.String(length=4), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_ts", "events", ["ts"])
    op.create_index("ix_events_user_hash_ts", "events", ["user_hash", "ts"])


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS events")
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
