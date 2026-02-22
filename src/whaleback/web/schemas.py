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
    financial_invest_net: int | None = None
    insurance_net: int | None = None
    trust_net: int | None = None
    private_equity_net: int | None = None
    bank_net: int | None = None
    other_financial_net: int | None = None
    other_corp_net: int | None = None
    other_foreign_net: int | None = None
    total_net: int | None = None


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
    net_total: int | None = Field(None, description="Net purchase total (KRW)")
    buy_days: int | None = None
    sell_days: int | None = None
    consistency: float | None = Field(None, description="Buy consistency ratio (0.0-1.0)")
    intensity: float | None = Field(None, description="Buying intensity ratio")
    score: float | None = Field(None, description="Component sub-score")


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
    private_equity_net: int | None = None
    other_corp_net: int | None = None


class WhaleTopItem(BaseModel):
    ticker: str
    name: str | None = None
    market: str | None = None
    whale_score: float | None = None
    signal: str | None = None
    institution_net_20d: int | None = None
    foreign_net_20d: int | None = None
    pension_net_20d: int | None = None
    private_equity_net_20d: int | None = None
    other_corp_net_20d: int | None = None


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


# --- Composite Analysis schemas ---


class FlowAnalysis(BaseModel):
    ticker: str
    trade_date: str
    retail_z: float | None = None
    retail_intensity: float | None = None
    retail_consistency: float | None = None
    retail_signal: str | None = None
    divergence_score: float | None = None
    smart_ratio: float | None = None
    dumb_ratio: float | None = None
    divergence_signal: str | None = None
    shift_score: float | None = None
    shift_signal: str | None = None


class TechnicalAnalysis(BaseModel):
    ticker: str
    trade_date: str
    disparity_20d: float | None = None
    disparity_60d: float | None = None
    disparity_120d: float | None = None
    disparity_signal: str | None = None
    bb_upper: float | None = None
    bb_center: float | None = None
    bb_lower: float | None = None
    bb_bandwidth: float | None = None
    bb_percent_b: float | None = None
    bb_signal: str | None = None
    macd_value: float | None = None
    macd_signal_line: float | None = None
    macd_histogram: float | None = None
    macd_crossover: str | None = None


class RiskAnalysis(BaseModel):
    ticker: str
    trade_date: str
    volatility_20d: float | None = None
    volatility_60d: float | None = None
    volatility_1y: float | None = None
    risk_level: str | None = None
    beta_60d: float | None = None
    beta_252d: float | None = None
    beta_interpretation: str | None = None
    mdd_60d: float | None = None
    mdd_1y: float | None = None
    current_drawdown: float | None = None
    recovery_label: str | None = None


class CompositeScore(BaseModel):
    ticker: str
    name: str | None = None
    trade_date: str
    composite_score: float | None = Field(None, description="WCS composite score (0-100)")
    value_score: float | None = Field(None, description="Value axis score (0-100)")
    flow_score: float | None = Field(None, description="Flow axis score (0-100)")
    momentum_score: float | None = Field(None, description="Momentum axis score (0-100)")
    forecast_score: float | None = Field(None, description="Forecast axis score (0-100)")
    sentiment_score: float | None = Field(None, description="Sentiment axis score (0-100)")
    confidence: float | None = Field(None, description="Score confidence (0.0-1.0)")
    axes_available: int | None = Field(None, description="Number of axes with data (0-4)")
    confluence_tier: int | None = Field(None, description="Signal confluence tier (1-5)")
    confluence_pattern: str | None = None
    divergence_type: str | None = None
    divergence_label: str | None = None
    action_label: str | None = Field(None, description="Action recommendation in Korean")
    action_description: str | None = None
    score_tier: str | None = Field(None, description="Score tier: excellent/good/fair/average/caution/risk")
    score_label: str | None = Field(None, description="Score tier in Korean")
    score_color: str | None = Field(None, description="UI color for the tier")


class CompositeDetail(BaseModel):
    """Full composite analysis including sub-analyses."""
    composite: CompositeScore
    flow: FlowAnalysis | None = None
    technical: TechnicalAnalysis | None = None
    risk: RiskAnalysis | None = None


class CompositeRankingItem(BaseModel):
    ticker: str
    name: str | None = None
    market: str | None = None
    composite_score: float | None = None
    value_score: float | None = None
    flow_score: float | None = None
    momentum_score: float | None = None
    forecast_score: float | None = None
    sentiment_score: float | None = None
    confluence_tier: int | None = None
    action_label: str | None = None
    score_tier: str | None = None
    score_label: str | None = None
    score_color: str | None = None


# --- Simulation schemas ---


class SimulationHorizon(BaseModel):
    label: str
    p5: int | None = None
    p25: int | None = None
    p50: int | None = None
    p75: int | None = None
    p95: int | None = None
    expected_return_pct: float | None = None
    var_5pct_pct: float | None = None
    upside_prob: float | None = None


class ModelScore(BaseModel):
    model: str
    score: float | None = None
    weight: float


class SimulationModelBreakdown(BaseModel):
    model_scores: list[ModelScore] | None = None
    model_weights: dict[str, float] | None = None
    ensemble_method: str | None = None


class SimulationResult(BaseModel):
    ticker: str
    name: str | None = None
    as_of_date: str
    base_price: int | None = None
    simulation_score: float | None = None
    simulation_grade: str | None = None
    mu: float | None = None
    sigma: float | None = None
    num_simulations: int | None = None
    input_days_used: int | None = None
    horizons: dict[str, SimulationHorizon] | None = None
    target_probs: dict[str, dict[str, float]] | None = None
    model_breakdown: SimulationModelBreakdown | None = None


class SimulationTopItem(BaseModel):
    ticker: str
    name: str | None = None
    market: str | None = None
    simulation_score: float | None = None
    simulation_grade: str | None = None
    base_price: int | None = None
    expected_return_pct_6m: float | None = None
    upside_prob_3m: float | None = None


# --- News Sentiment schemas ---


class NewsSnapshot(BaseModel):
    ticker: str
    name: str | None = None
    trade_date: str
    sentiment_score: float | None = Field(None, description="Normalized sentiment score (0-100)")
    direction: float | None = Field(None, description="Sentiment direction D ∈ [-1, +1]")
    intensity: float | None = Field(None, description="Reaction intensity I ∈ [0, 1]")
    confidence: float | None = Field(None, description="Agreement confidence C ∈ [0, 1]")
    effective_score: float | None = Field(None, description="Effective score S_eff = D × I × C")
    sentiment_signal: str | None = Field(None, description="Signal: strong_buy/buy/neutral/sell/strong_sell")
    article_count: int | None = None
    status: str | None = Field(None, description="Status: active/stale/insufficient/no_data")
    source_breakdown: dict[str, Any] | None = None


class NewsTopItem(BaseModel):
    ticker: str
    name: str | None = None
    market: str | None = None
    sentiment_score: float | None = None
    sentiment_signal: str | None = None
    article_count: int | None = None
    direction: float | None = None
    effective_score: float | None = None


# --- Sector Flow schemas ---


class SectorFlowItem(BaseModel):
    net_purchase: int | None = None
    intensity: float | None = None
    consistency: float | None = None
    signal: str | None = None
    trend_5d: int | None = None
    trend_20d: int | None = None


class SectorFlowOverviewItem(BaseModel):
    sector: str
    flows: dict[str, SectorFlowItem]
    stock_count: int
    dominant_signal: str | None = None


class SectorFlowHeatmapData(BaseModel):
    sectors: list[str]
    investor_types: list[str]
    matrix: list[list[float | None]]
    signals: list[list[str | None]]


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
