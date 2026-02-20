from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Stock(Base):
    __tablename__ = "stocks"

    ticker: Mapped[str] = mapped_column(String(6), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    market: Mapped[str] = mapped_column(String(6), nullable=False)
    listed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    delisted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DailyOHLCV(Base):
    __tablename__ = "daily_ohlcv"
    __table_args__ = ({"postgresql_partition_by": "RANGE (trade_date)"},)

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(6), primary_key=True)
    open: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    high: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    low: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    close: Mapped[int] = mapped_column(BigInteger, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    trading_value: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    change_rate: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Fundamental(Base):
    __tablename__ = "fundamentals"
    __table_args__ = ({"postgresql_partition_by": "RANGE (trade_date)"},)

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(6), primary_key=True)
    bps: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    per: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    pbr: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    eps: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    div: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    dps: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    roe: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class InvestorTrading(Base):
    __tablename__ = "investor_trading"
    __table_args__ = ({"postgresql_partition_by": "RANGE (trade_date)"},)

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(6), primary_key=True)
    institution_net: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    foreign_net: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    individual_net: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    pension_net: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    financial_invest_net: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    insurance_net: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    trust_net: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    private_equity_net: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    bank_net: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    other_financial_net: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    other_corp_net: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    other_foreign_net: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_net: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CollectionLog(Base):
    __tablename__ = "collection_log"
    __table_args__ = (
        UniqueConstraint("collection_type", "target_date", name="uq_collection_type_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    records_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SectorMapping(Base):
    __tablename__ = "sector_mapping"

    ticker: Mapped[str] = mapped_column(String(6), primary_key=True)
    sector: Mapped[str] = mapped_column(String(50), nullable=False)
    sector_en: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sub_sector: Mapped[str | None] = mapped_column(String(50), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class MarketIndex(Base):
    __tablename__ = "market_index"
    __table_args__ = ({"postgresql_partition_by": "RANGE (trade_date)"},)

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    index_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    index_name: Mapped[str] = mapped_column(String(50), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    change_rate: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    trading_value: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AnalysisQuantSnapshot(Base):
    __tablename__ = "analysis_quant_snapshot"
    __table_args__ = ({"postgresql_partition_by": "RANGE (trade_date)"},)

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(6), primary_key=True)
    rim_value: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    safety_margin: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    fscore: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fscore_detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    investment_grade: Mapped[str | None] = mapped_column(String(3), nullable=True)
    data_completeness: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AnalysisWhaleSnapshot(Base):
    __tablename__ = "analysis_whale_snapshot"
    __table_args__ = ({"postgresql_partition_by": "RANGE (trade_date)"},)

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(6), primary_key=True)
    whale_score: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    institution_net_20d: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    foreign_net_20d: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    pension_net_20d: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    institution_consistency: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    foreign_consistency: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    pension_consistency: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    signal: Mapped[str | None] = mapped_column(String(30), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AnalysisTrendSnapshot(Base):
    __tablename__ = "analysis_trend_snapshot"
    __table_args__ = ({"postgresql_partition_by": "RANGE (trade_date)"},)

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(6), primary_key=True)
    rs_vs_kospi_20d: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    rs_vs_kospi_60d: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    rs_percentile: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sector: Mapped[str | None] = mapped_column(String(50), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
