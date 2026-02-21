// API response types matching backend schemas

export interface Meta {
  timestamp: string;
  cached: boolean;
}

export interface PaginatedMeta extends Meta {
  total: number;
  page: number;
  size: number;
}

export interface ApiResponse<T> {
  data: T;
  meta: Meta;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: PaginatedMeta;
}

// Stock types
export interface StockSummary {
  ticker: string;
  name: string;
  market: string;
  is_active: boolean;
  sector?: string | null;
  latest_close?: number | null;
  change_rate?: number | null;
  latest_date?: string | null;
}

export interface PriceData {
  trade_date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number;
  volume: number;
  trading_value: number | null;
  change_rate: number | null;
}

export interface FundamentalData {
  trade_date: string;
  bps: number | null;
  per: number | null;
  pbr: number | null;
  eps: number | null;
  div: number | null;
  dps: number | null;
  roe: number | null;
}

export interface StockDetail {
  ticker: string;
  name: string;
  market: string;
  is_active: boolean;
  listed_date: string | null;
  delisted_date: string | null;
  sector: string | null;
  latest_price: PriceData | null;
  latest_fundamental: FundamentalData | null;
}

export interface InvestorData {
  trade_date: string;
  institution_net: number | null;
  foreign_net: number | null;
  individual_net: number | null;
  pension_net: number | null;
  private_equity_net: number | null;
  other_corp_net: number | null;
}

// Quant types
export interface FScoreCriterion {
  name: string;
  score: number;
  value: number | null;
  label: string;
  note?: string | null;
}

export interface QuantValuation {
  ticker: string;
  name: string | null;
  as_of_date: string;
  current_price: number | null;
  rim_value: number | null;
  safety_margin_pct: number | null;
  is_undervalued: boolean | null;
  grade: string | null;
  grade_label: string | null;
}

export interface FScoreDetail {
  ticker: string;
  total_score: number;
  max_score: number;
  criteria: FScoreCriterion[];
  data_completeness: number;
}

export interface QuantRankingItem {
  ticker: string;
  name: string | null;
  market: string | null;
  rim_value: number | null;
  safety_margin: number | null;
  fscore: number | null;
  investment_grade: string | null;
  data_completeness: number | null;
}

// Whale types
export interface WhaleScore {
  ticker: string;
  name: string | null;
  as_of_date: string;
  lookback_days: number;
  whale_score: number;
  signal: string;
  signal_label: string;
  components: Record<string, {
    net_total: number;
    consistency: number;
  }> | null;
}

export interface WhaleTopItem {
  ticker: string;
  name: string | null;
  market: string | null;
  whale_score: number | null;
  signal: string | null;
  institution_net_20d: number | null;
  foreign_net_20d: number | null;
  pension_net_20d: number | null;
  private_equity_net_20d: number | null;
  other_corp_net_20d: number | null;
}

// Trend types
export interface SectorRankingItem {
  sector: string;
  stock_count: number;
  avg_rs_percentile: number | null;
  avg_rs_20d: number | null;
  momentum_rank: number | null;
  quadrant: string | null;
}

export interface RSPoint {
  date?: string;
  stock_indexed: number;
  index_indexed: number;
  rs_ratio: number | null;
}

export interface RelativeStrength {
  ticker: string;
  name: string | null;
  benchmark: string;
  current_rs: number | null;
  rs_percentile: number | null;
  rs_change_pct: number | null;
  series: RSPoint[];
}

// Composite (WCS) types
export interface FlowAnalysis {
  ticker: string;
  trade_date: string;
  retail_z: number | null;
  retail_intensity: number | null;
  retail_consistency: number | null;
  retail_signal: string | null;
  divergence_score: number | null;
  smart_ratio: number | null;
  dumb_ratio: number | null;
  divergence_signal: string | null;
  shift_score: number | null;
  shift_signal: string | null;
}

export interface TechnicalAnalysis {
  ticker: string;
  trade_date: string;
  disparity_20d: number | null;
  disparity_60d: number | null;
  disparity_120d: number | null;
  disparity_signal: string | null;
  bb_upper: number | null;
  bb_center: number | null;
  bb_lower: number | null;
  bb_bandwidth: number | null;
  bb_percent_b: number | null;
  bb_signal: string | null;
  macd_value: number | null;
  macd_signal_line: number | null;
  macd_histogram: number | null;
  macd_crossover: string | null;
}

export interface RiskAnalysis {
  ticker: string;
  trade_date: string;
  volatility_20d: number | null;
  volatility_60d: number | null;
  volatility_1y: number | null;
  risk_level: string | null;
  beta_60d: number | null;
  beta_252d: number | null;
  beta_interpretation: string | null;
  mdd_60d: number | null;
  mdd_1y: number | null;
  current_drawdown: number | null;
  recovery_label: string | null;
}

export interface CompositeScore {
  ticker: string;
  name: string | null;
  trade_date: string;
  composite_score: number | null;
  value_score: number | null;
  flow_score: number | null;
  momentum_score: number | null;
  forecast_score: number | null;
  confidence: number | null;
  axes_available: number | null;
  confluence_tier: number | null;
  confluence_pattern: string | null;
  divergence_type: string | null;
  divergence_label: string | null;
  action_label: string | null;
  action_description: string | null;
  score_tier: string | null;
  score_label: string | null;
  score_color: string | null;
}

export interface CompositeDetail {
  composite: CompositeScore;
  flow: FlowAnalysis | null;
  technical: TechnicalAnalysis | null;
  risk: RiskAnalysis | null;
}

export interface CompositeRankingItem {
  ticker: string;
  name: string | null;
  market: string | null;
  composite_score: number | null;
  value_score: number | null;
  flow_score: number | null;
  momentum_score: number | null;
  forecast_score: number | null;
  confluence_tier: number | null;
  action_label: string | null;
  score_tier: string | null;
  score_label: string | null;
  score_color: string | null;
}

// Simulation types
export interface SimulationHorizon {
  label: string;
  p5: number | null;
  p25: number | null;
  p50: number | null;
  p75: number | null;
  p95: number | null;
  expected_return_pct: number | null;
  var_5pct_pct: number | null;
  upside_prob: number | null;
}

export interface SimulationResult {
  ticker: string;
  name: string | null;
  trade_date: string;
  simulation_score: number | null;
  simulation_grade: string | null;
  base_price: number | null;
  mu: number | null;
  sigma: number | null;
  num_simulations: number | null;
  input_days_used: number | null;
  horizons: Record<string, SimulationHorizon> | null;
  target_probs: Record<string, Record<string, number>> | null;
}

export interface SimulationTopItem {
  ticker: string;
  name: string | null;
  market: string | null;
  simulation_score: number | null;
  simulation_grade: string | null;
  base_price: number | null;
  expected_return_pct_6m: number | null;
  upside_prob_3m: number | null;
}

// Sector Flow types
export interface SectorFlowItem {
  net_purchase: number | null;
  intensity: number | null;
  consistency: number | null;
  signal: string | null;
  trend_5d: number | null;
  trend_20d: number | null;
}

export interface SectorFlowOverviewItem {
  sector: string;
  flows: Record<string, SectorFlowItem>;
  dominant_signal: string | null;
}

export interface SectorFlowHeatmapData {
  sectors: string[];
  investor_types: string[];
  matrix: number[][];
  metric: string;
}

// System types
export interface HealthResponse {
  status: string;
  version: string;
  cache_type: string;
}

export interface CollectionStatus {
  collection_type: string;
  target_date: string;
  status: string;
  records_count: number;
}
