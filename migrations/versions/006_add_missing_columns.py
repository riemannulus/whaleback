"""Add columns that were only in init-db ALTER TABLE list but missing from migrations

Fixes: sentiment_applied on analysis_simulation_snapshot (should have been in 004)

Revision ID: 006
Revises: 005
Create Date: 2026-02-26
"""
from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use IF NOT EXISTS for idempotency (safe on DBs that already ran init-db)
    op.execute(
        "ALTER TABLE analysis_simulation_snapshot "
        "ADD COLUMN IF NOT EXISTS sentiment_applied BOOLEAN DEFAULT FALSE"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE analysis_simulation_snapshot "
        "DROP COLUMN IF EXISTS sentiment_applied"
    )
