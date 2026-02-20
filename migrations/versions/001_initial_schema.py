"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Stocks master table
    op.create_table(
        "stocks",
        sa.Column("ticker", sa.String(6), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("market", sa.String(6), nullable=False),
        sa.Column("listed_date", sa.Date(), nullable=True),
        sa.Column("delisted_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_stocks_market", "stocks", ["market"])
    op.create_index("idx_stocks_active", "stocks", ["is_active"], postgresql_where=sa.text("is_active = TRUE"))

    # Daily OHLCV (partitioned)
    op.execute("""
        CREATE TABLE daily_ohlcv (
            trade_date DATE NOT NULL,
            ticker VARCHAR(6) NOT NULL,
            open BIGINT,
            high BIGINT,
            low BIGINT,
            close BIGINT NOT NULL,
            volume BIGINT NOT NULL DEFAULT 0,
            trading_value BIGINT,
            change_rate NUMERIC(8, 4),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (trade_date, ticker)
        ) PARTITION BY RANGE (trade_date)
    """)

    # Fundamentals (partitioned)
    op.execute("""
        CREATE TABLE fundamentals (
            trade_date DATE NOT NULL,
            ticker VARCHAR(6) NOT NULL,
            bps NUMERIC(12, 2),
            per NUMERIC(10, 2),
            pbr NUMERIC(10, 4),
            eps NUMERIC(12, 2),
            div NUMERIC(8, 4),
            dps NUMERIC(12, 2),
            roe NUMERIC(10, 4),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (trade_date, ticker)
        ) PARTITION BY RANGE (trade_date)
    """)

    # Investor trading (partitioned)
    op.execute("""
        CREATE TABLE investor_trading (
            trade_date DATE NOT NULL,
            ticker VARCHAR(6) NOT NULL,
            institution_net BIGINT,
            foreign_net BIGINT,
            individual_net BIGINT,
            pension_net BIGINT,
            financial_invest_net BIGINT,
            insurance_net BIGINT,
            trust_net BIGINT,
            private_equity_net BIGINT,
            bank_net BIGINT,
            other_financial_net BIGINT,
            other_corp_net BIGINT,
            other_foreign_net BIGINT,
            total_net BIGINT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (trade_date, ticker)
        ) PARTITION BY RANGE (trade_date)
    """)

    # Create partitions (2020-2027)
    for table in ("daily_ohlcv", "fundamentals", "investor_trading"):
        for year in range(2020, 2028):
            op.execute(f"""
                CREATE TABLE {table}_{year} PARTITION OF {table}
                FOR VALUES FROM ('{year}-01-01') TO ('{year + 1}-01-01')
            """)

    # Create indexes on partitioned tables
    op.execute("CREATE INDEX idx_ohlcv_ticker ON daily_ohlcv (ticker, trade_date DESC)")
    op.execute("CREATE INDEX idx_fundamentals_ticker ON fundamentals (ticker, trade_date DESC)")
    op.execute("CREATE INDEX idx_investor_ticker ON investor_trading (ticker, trade_date DESC)")

    # Collection log
    op.create_table(
        "collection_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("collection_type", sa.String(30), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("records_count", sa.Integer(), default=0),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("collection_type", "target_date", name="uq_collection_type_date"),
    )
    op.create_index("idx_collection_log_date", "collection_log", ["target_date"])


def downgrade() -> None:
    op.drop_table("collection_log")
    for table in ("investor_trading", "fundamentals", "daily_ohlcv"):
        for year in range(2020, 2028):
            op.execute(f"DROP TABLE IF EXISTS {table}_{year}")
        op.execute(f"DROP TABLE IF EXISTS {table}")
    op.drop_table("stocks")
