"""Whale expansion, simulation, sector flow, WCS 4-axis

Revision ID: 002
Revises: 001
Create Date: 2026-02-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Feature 1: Add new investor columns to investor_trading ---
    # These were already in 001 schema (financial_invest_net through total_net)
    # So no ALTER TABLE needed for investor_trading.

    # --- Feature 1: Add whale expansion columns to analysis_whale_snapshot ---
    op.add_column("analysis_whale_snapshot", sa.Column("private_equity_net_20d", sa.BigInteger(), nullable=True))
    op.add_column("analysis_whale_snapshot", sa.Column("other_corp_net_20d", sa.BigInteger(), nullable=True))
    op.add_column("analysis_whale_snapshot", sa.Column("private_equity_consistency", sa.Numeric(4, 2), nullable=True))
    op.add_column("analysis_whale_snapshot", sa.Column("other_corp_consistency", sa.Numeric(4, 2), nullable=True))

    # --- Feature 3: analysis_simulation_snapshot (partitioned) ---
    op.execute("""
        CREATE TABLE analysis_simulation_snapshot (
            trade_date DATE NOT NULL,
            ticker VARCHAR(6) NOT NULL,
            simulation_score NUMERIC(6, 2),
            simulation_grade VARCHAR(20),
            base_price BIGINT,
            mu NUMERIC(10, 6),
            sigma NUMERIC(10, 6),
            num_simulations INTEGER,
            input_days_used INTEGER,
            horizons JSONB,
            target_probs JSONB,
            computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (trade_date, ticker)
        ) PARTITION BY RANGE (trade_date)
    """)

    # Create partitions 2020-2028
    for year in range(2020, 2029):
        op.execute(f"""
            CREATE TABLE analysis_simulation_snapshot_{year}
            PARTITION OF analysis_simulation_snapshot
            FOR VALUES FROM ('{year}-01-01') TO ('{year + 1}-01-01')
        """)

    # Indexes for simulation
    op.execute("CREATE INDEX idx_simulation_score ON analysis_simulation_snapshot (trade_date, simulation_score DESC)")
    op.execute("CREATE INDEX idx_simulation_grade ON analysis_simulation_snapshot (trade_date, simulation_grade)")

    # --- Feature 2: analysis_sector_flow_snapshot (partitioned, triple PK) ---
    op.execute("""
        CREATE TABLE analysis_sector_flow_snapshot (
            trade_date DATE NOT NULL,
            sector VARCHAR(50) NOT NULL,
            investor_type VARCHAR(30) NOT NULL,
            net_purchase BIGINT,
            intensity NUMERIC(8, 4),
            consistency NUMERIC(4, 2),
            signal VARCHAR(30),
            trend_5d BIGINT,
            trend_20d BIGINT,
            stock_count INTEGER,
            computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (trade_date, sector, investor_type)
        ) PARTITION BY RANGE (trade_date)
    """)

    # Create partitions 2020-2028
    for year in range(2020, 2029):
        op.execute(f"""
            CREATE TABLE analysis_sector_flow_snapshot_{year}
            PARTITION OF analysis_sector_flow_snapshot
            FOR VALUES FROM ('{year}-01-01') TO ('{year + 1}-01-01')
        """)

    # Indexes for sector flow
    op.execute("CREATE INDEX idx_sector_flow_signal ON analysis_sector_flow_snapshot (trade_date, signal)")
    op.execute("CREATE INDEX idx_sector_flow_sector ON analysis_sector_flow_snapshot (trade_date, sector, investor_type)")

    # --- Feature 4: Add forecast_score to analysis_composite_snapshot ---
    op.add_column("analysis_composite_snapshot", sa.Column("forecast_score", sa.Numeric(6, 2), nullable=True))


def downgrade() -> None:
    # Drop forecast_score
    op.drop_column("analysis_composite_snapshot", "forecast_score")

    # Drop sector flow
    for year in range(2020, 2029):
        op.execute(f"DROP TABLE IF EXISTS analysis_sector_flow_snapshot_{year}")
    op.execute("DROP TABLE IF EXISTS analysis_sector_flow_snapshot")

    # Drop simulation
    for year in range(2020, 2029):
        op.execute(f"DROP TABLE IF EXISTS analysis_simulation_snapshot_{year}")
    op.execute("DROP TABLE IF EXISTS analysis_simulation_snapshot")

    # Drop whale expansion columns
    op.drop_column("analysis_whale_snapshot", "other_corp_consistency")
    op.drop_column("analysis_whale_snapshot", "private_equity_consistency")
    op.drop_column("analysis_whale_snapshot", "other_corp_net_20d")
    op.drop_column("analysis_whale_snapshot", "private_equity_net_20d")
