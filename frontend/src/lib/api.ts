const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function fetchApi<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    });
  }

  const res = await fetch(url.toString());

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }

  return res.json();
}

// Stock API
export const stocksApi = {
  list: (params?: { market?: string; search?: string; page?: number; size?: number }) =>
    fetchApi<any>("/api/v1/stocks", params),

  detail: (ticker: string) =>
    fetchApi<any>(`/api/v1/stocks/${ticker}`),

  price: (ticker: string, params?: { start_date?: string; end_date?: string }) =>
    fetchApi<any>(`/api/v1/stocks/${ticker}/price`, params),

  investors: (ticker: string, params?: { start_date?: string; end_date?: string }) =>
    fetchApi<any>(`/api/v1/stocks/${ticker}/investors`, params),
};

// Quant API
export const quantApi = {
  valuation: (ticker: string) =>
    fetchApi<any>(`/api/v1/analysis/quant/valuation/${ticker}`),

  fscore: (ticker: string) =>
    fetchApi<any>(`/api/v1/analysis/quant/fscore/${ticker}`),

  grade: (ticker: string) =>
    fetchApi<any>(`/api/v1/analysis/quant/grade/${ticker}`),

  rankings: (params?: { market?: string; min_fscore?: number; grade?: string; sort_by?: string; page?: number; size?: number }) =>
    fetchApi<any>("/api/v1/analysis/quant/rankings", params),
};

// Whale API
export const whaleApi = {
  score: (ticker: string) =>
    fetchApi<any>(`/api/v1/analysis/whale/score/${ticker}`),

  accumulation: (ticker: string, params?: { start_date?: string; end_date?: string }) =>
    fetchApi<any>(`/api/v1/analysis/whale/accumulation/${ticker}`, params),

  top: (params?: { market?: string; min_score?: number; signal?: string; page?: number; size?: number }) =>
    fetchApi<any>("/api/v1/analysis/whale/top", params),
};

// Trend API
export const trendApi = {
  sectorRanking: (params?: { market?: string }) =>
    fetchApi<any>("/api/v1/analysis/trend/sector-ranking", params),

  relativeStrength: (ticker: string, params?: { benchmark?: string; days?: number }) =>
    fetchApi<any>(`/api/v1/analysis/trend/relative-strength/${ticker}`, params),

  sectorRotation: (params?: { market?: string }) =>
    fetchApi<any>("/api/v1/analysis/trend/sector-rotation", params),

  sectorStocks: (sectorName: string, params?: { page?: number; size?: number }) =>
    fetchApi<any>(`/api/v1/analysis/trend/sector/${encodeURIComponent(sectorName)}`, params),
};

// Composite API
export const compositeApi = {
  score: (ticker: string) =>
    fetchApi<any>(`/api/v1/analysis/composite/score/${ticker}`),

  detail: (ticker: string) =>
    fetchApi<any>(`/api/v1/analysis/composite/detail/${ticker}`),

  rankings: (params?: { market?: string; min_score?: number; min_confluence?: number; score_tier?: string; sort_by?: string; page?: number; size?: number }) =>
    fetchApi<any>("/api/v1/analysis/composite/rankings", params),
};

// Simulation API
export const simulationApi = {
  result: (ticker: string) =>
    fetchApi<any>(`/api/v1/analysis/simulation/${ticker}`),

  rankings: (params?: { market?: string; min_score?: number; page?: number; size?: number }) =>
    fetchApi<any>("/api/v1/analysis/simulation/top", params),
};

// News Sentiment API
export const newsApi = {
  sentiment: (ticker: string) =>
    fetchApi<any>(`/api/v1/analysis/news-sentiment/${ticker}`),

  top: (params?: { market?: string; min_score?: number; signal?: string; page?: number; size?: number }) =>
    fetchApi<any>("/api/v1/analysis/news-sentiment/top", params),
};

// Sector Flow API
export const sectorFlowApi = {
  overview: () =>
    fetchApi<any>("/api/v1/analysis/sector-flow/overview"),

  sector: (sectorName: string) =>
    fetchApi<any>(`/api/v1/analysis/sector-flow/sector/${encodeURIComponent(sectorName)}`),

  heatmap: (params?: { metric?: string }) =>
    fetchApi<any>("/api/v1/analysis/sector-flow/heatmap", params),
};

// Market Summary API
export const marketSummaryApi = {
  getLatest: () => fetchApi<any>("/api/v1/analysis/market-summary"),
  getByDate: (date: string) => fetchApi<any>(`/api/v1/analysis/market-summary/${date}`),
  getHistory: (limit?: number) => fetchApi<any>(`/api/v1/analysis/market-summary/history?limit=${limit || 10}`),
};

// System API
export const systemApi = {
  health: () => fetchApi<any>("/api/v1/health"),
  pipeline: () => fetchApi<any>("/api/v1/health/pipeline"),
};
