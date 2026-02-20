"""Pydantic response schemas for Whaleback API."""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# --- Base schemas ---


class Meta(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cached: bool = False


class PaginatedMeta(Meta):
    total: int
    page: int
    size: int


class ApiResponse(BaseModel, Generic[T]):
    data: T
    meta: Meta = Field(default_factory=Meta)


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    meta: PaginatedMeta


class ErrorResponse(BaseModel):
    error: dict[str, Any] = Field(
        description="Error details with code, message, and optional detail"
    )


# --- Stock schemas ---


class StockSummary(BaseModel):
    ticker: str = Field(description="6-digit stock ticker code")
    name: str = Field(description="Stock name in Korean")
    market: str = Field(description="KOSPI or KOSDAQ")
    is_active: bool = Field(description="Whether stock is currently listed")
    sector: str | None = Field(None, description="Sector classification")
    latest_close: int | None = Field(None, description="Latest closing price (KRW)")
    change_rate: float | None = Field(None, description="Latest daily change rate (%)")
    latest_date: str | None = Field(None, description="Latest trade date")


class PriceData(BaseModel):
    trade_date: str
    open: int | None = None
    high: int | None = None
    low: int | None = None
    close: int
    volume: int
    trading_value: int | None = None
    change_rate: float | None = None


class FundamentalData(BaseModel):
    trade_date: str
    bps: float | None = None
    per: float | None = None
    pbr: float | None = None
    eps: float | None = None
    div: float | None = None
    dps: float | None = None
    roe: float | None = None


class StockDetail(BaseModel):
    ticker: str
    name: str
    market: str
    is_active: bool
    listed_date: str | None = None
    delisted_date: str | None = None
    sector: str | None = None
    latest_price: PriceData | None = None
    latest_fundamental: FundamentalData | None = None


class InvestorData(BaseModel):
    trade_date: str
    institution_net: int | None = None
    foreign_net: int | None = None
    individual_net: int | None = None
    pension_net: int | None = None


# --- Quant Analysis schemas ---


class FScoreCriterion(BaseModel):
    name: str = Field(description="Criterion identifier")
    score: int = Field(description="0 or 1")
    value: float | None = Field(None, description="Computed value")
    label: str = Field(description="Korean description")
    note: str | None = Field(None, description="Additional note if data is missing")


class QuantValuation(BaseModel):
    ticker: str
    name: str | None = None
    as_of_date: str
    current_price: int | None = None
    rim_value: float | None = Field(None, description="RIM intrinsic value")
    safety_margin_pct: float | None = Field(None, description="Safety margin percentage")
    is_undervalued: bool | None = None
    inputs: dict[str, Any] | None = Field(None, description="RIM input parameters")
    grade: str | None = Field(None, description="Investment grade (A+ to F)")
    grade_label: str | None = Field(None, description="Grade description in Korean")


class FScoreResponse(BaseModel):
    ticker: str
    total_score: int = Field(description="F-Score (0-9)")
    max_score: int = 9
    criteria: list[FScoreCriterion] = Field(description="Individual criteria scores")
    data_completeness: float = Field(description="Ratio of computable signals (0.0-1.0)")


class QuantRankingItem(BaseModel):
    ticker: str
    name: str | None = None
    market: str | None = None
    rim_value: float | None = None
    safety_margin: float | None = None
    fscore: int | None = None
    investment_grade: str | None = None
    data_completeness: float | None = None


# --- Whale Analysis schemas ---


class WhaleComponent(BaseModel):
    net_total: int = Field(description="Net purchase total (KRW)")
    buy_days: int
    sell_days: int
    consistency: float = Field(description="Buy consistency ratio (0.0-1.0)")
    intensity: float = Field(description="Buying intensity ratio")
    score: float = Field(description="Component sub-score")


class WhaleScore(BaseModel):
    ticker: str
    name: str | None = None
    as_of_date: str
    lookback_days: int
    whale_score: float = Field(description="Composite whale score (0-100)")
    components: dict[str, WhaleComponent] | None = None
    signal: str = Field(description="Signal classification")
    signal_label: str = Field(description="Signal in Korean")


class WhaleAccumulationDay(BaseModel):
    trade_date: str
    institution_net: int | None = None
    foreign_net: int | None = None
    pension_net: int | None = None


class WhaleTopItem(BaseModel):
    ticker: str
    name: str | None = None
    market: str | None = None
    whale_score: float | None = None
    signal: str | None = None
    institution_net_20d: int | None = None
    foreign_net_20d: int | None = None
    pension_net_20d: int | None = None


# --- Trend Analysis schemas ---


class SectorRankingItem(BaseModel):
    sector: str
    stock_count: int
    avg_rs_percentile: float | None = None
    avg_rs_20d: float | None = None
    momentum_rank: int | None = None
    quadrant: str | None = Field(
        None, description="Rotation quadrant: leading/weakening/lagging/improving"
    )


class RSPoint(BaseModel):
    date: str | None = None
    stock_indexed: float
    index_indexed: float
    rs_ratio: float | None = None


class RelativeStrength(BaseModel):
    ticker: str
    name: str | None = None
    benchmark: str = "KOSPI"
    current_rs: float | None = None
    rs_percentile: int | None = None
    rs_change_pct: float | None = None
    series: list[RSPoint] = []


class SectorDetail(BaseModel):
    sector: str
    stock_count: int
    stocks: list[StockSummary] = []


# --- System schemas ---


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.2.0"
    service: str = "whaleback-api"
    db_connected: bool = True
    cache_type: str = "memory"


class CollectionStatus(BaseModel):
    collection_type: str
    target_date: str
    status: str
    records_count: int
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None


class PipelineStatus(BaseModel):
    collections: list[CollectionStatus]
