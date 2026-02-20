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
