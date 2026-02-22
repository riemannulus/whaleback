"""Add news sentiment tables and sentiment_score to composite snapshot

Revision ID: 004
Revises: 003
Create Date: 2026-02-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create news_articles table
    op.create_table(
        "news_articles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(6), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_name", sa.String(100), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("sentiment_raw", sa.Numeric(5, 4), nullable=True),
        sa.Column("sentiment_label", sa.String(20), nullable=True),
        sa.Column("sentiment_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("scoring_method", sa.String(20), nullable=True),
        sa.Column("article_type", sa.String(30), nullable=True),
        sa.Column("source_type", sa.String(20), nullable=True),
        sa.Column(
            "importance_weight", sa.Numeric(4, 2), nullable=True, server_default="1.0"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker", "source_url", name="uq_news_ticker_url"),
    )

    # 2. Index on (ticker, published_at DESC)
    op.create_index(
        "idx_news_ticker_date",
        "news_articles",
        ["ticker", sa.text("published_at DESC")],
    )

    # Also create index declared via index=True on ticker column
    op.create_index(
        op.f("ix_news_articles_ticker"),
        "news_articles",
        ["ticker"],
        unique=False,
    )

    # 3. Create analysis_news_snapshot table (partitioned by trade_date RANGE)
    op.execute(
        """
        CREATE TABLE analysis_news_snapshot (
            trade_date      DATE        NOT NULL,
            ticker          VARCHAR(6)  NOT NULL,
            sentiment_score NUMERIC(6,2),
            direction       NUMERIC(5,4),
            intensity       NUMERIC(4,3),
            confidence      NUMERIC(4,3),
            effective_score NUMERIC(5,4),
            sentiment_signal VARCHAR(30),
            article_count   INTEGER,
            status          VARCHAR(20),
            source_breakdown JSONB,
            computed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (trade_date, ticker)
        ) PARTITION BY RANGE (trade_date)
        """
    )

    # 4. Add sentiment_score to analysis_composite_snapshot
    op.add_column(
        "analysis_composite_snapshot",
        sa.Column("sentiment_score", sa.Numeric(6, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("analysis_composite_snapshot", "sentiment_score")
    op.execute("DROP TABLE IF EXISTS analysis_news_snapshot")
    op.drop_index("idx_news_ticker_date", table_name="news_articles")
    op.drop_index(op.f("ix_news_articles_ticker"), table_name="news_articles")
    op.drop_table("news_articles")
