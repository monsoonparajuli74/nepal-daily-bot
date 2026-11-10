"""Add per-user daily briefing opt-out.

Revision ID: 0002_daily_briefing_opt_out
Revises: 0001_initial
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0002_daily_briefing_opt_out"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("users")}
    if "daily_briefing_opt_out" not in columns:
        op.add_column(
            "users",
            sa.Column("daily_briefing_opt_out", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("users")}
    if "daily_briefing_opt_out" in columns:
        op.drop_column("users", "daily_briefing_opt_out")
