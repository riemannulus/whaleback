"""Add market_summary table for AI-powered market analysis reports

Revision ID: 005
Revises: 004
Create Date: 2026-02-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_summary",
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("full_report", sa.Text(), nullable=False),
        sa.Column("dashboard_summary", sa.Text(), nullable=False),
        sa.Column("key_insights", postgresql.JSONB(), nullable=True),
        sa.Column("sector_highlights", postgresql.JSONB(), nullable=True),
        sa.Column("model_used", sa.String(50), nullable=False),
        sa.Column("condenser_model_used", sa.String(50), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("trade_date"),
    )


def downgrade() -> None:
    op.drop_table("market_summary")
