import { useQuery } from "@tanstack/react-query";
import { stocksApi, quantApi, whaleApi, trendApi, systemApi } from "./api";
import type {
  PaginatedResponse, ApiResponse, StockSummary, StockDetail,
  PriceData, InvestorData, QuantValuation, FScoreDetail,
  QuantRankingItem, WhaleScore, WhaleTopItem, SectorRankingItem,
  RelativeStrength, HealthResponse,
} from "@/types/api";

// Stock hooks
export function useStocks(params?: { market?: string; search?: string; page?: number; size?: number }) {
  return useQuery({
    queryKey: ["stocks", params],
    queryFn: () => stocksApi.list(params),
  });
}

export function useStockDetail(ticker: string) {
  return useQuery({
    queryKey: ["stock", ticker],
    queryFn: () => stocksApi.detail(ticker),
    enabled: !!ticker,
  });
}

export function usePriceHistory(ticker: string, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["price", ticker, startDate, endDate],
    queryFn: () => stocksApi.price(ticker, { start_date: startDate, end_date: endDate }),
    enabled: !!ticker,
  });
}

export function useInvestorHistory(ticker: string, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["investors", ticker, startDate, endDate],
    queryFn: () => stocksApi.investors(ticker, { start_date: startDate, end_date: endDate }),
    enabled: !!ticker,
  });
}

// Quant hooks
export function useQuantValuation(ticker: string) {
  return useQuery({
    queryKey: ["quant", "valuation", ticker],
    queryFn: () => quantApi.valuation(ticker),
    enabled: !!ticker,
  });
}

export function useFScore(ticker: string) {
  return useQuery({
    queryKey: ["quant", "fscore", ticker],
    queryFn: () => quantApi.fscore(ticker),
    enabled: !!ticker,
  });
}

export function useQuantRankings(params?: { market?: string; min_fscore?: number; grade?: string; sort_by?: string; page?: number; size?: number }) {
  return useQuery({
    queryKey: ["quant", "rankings", params],
    queryFn: () => quantApi.rankings(params),
  });
}

// Whale hooks
export function useWhaleScore(ticker: string) {
  return useQuery({
    queryKey: ["whale", "score", ticker],
    queryFn: () => whaleApi.score(ticker),
    enabled: !!ticker,
  });
}

export function useWhaleTop(params?: { market?: string; min_score?: number; signal?: string; page?: number; size?: number }) {
  return useQuery({
    queryKey: ["whale", "top", params],
    queryFn: () => whaleApi.top(params),
  });
}

// Trend hooks
export function useSectorRanking(params?: { market?: string }) {
  return useQuery({
    queryKey: ["trend", "sectors", params],
    queryFn: () => trendApi.sectorRanking(params),
  });
}

export function useRelativeStrength(ticker: string, benchmark?: string) {
  return useQuery({
    queryKey: ["trend", "rs", ticker, benchmark],
    queryFn: () => trendApi.relativeStrength(ticker, { benchmark }),
    enabled: !!ticker,
  });
}

export function useSectorRotation(params?: { market?: string }) {
  return useQuery({
    queryKey: ["trend", "rotation", params],
    queryFn: () => trendApi.sectorRotation(params),
  });
}

// System hooks
export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => systemApi.health(),
    refetchInterval: 60000,
  });
}

export function usePipelineStatus() {
  return useQuery({
    queryKey: ["pipeline"],
    queryFn: () => systemApi.pipeline(),
  });
}
