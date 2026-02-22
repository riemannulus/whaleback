"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useStockDetail, usePriceHistory, useInvestorHistory } from "@/lib/queries";
import { CandlestickChart } from "@/components/charts/candlestick-chart";
import { LineChart } from "@/components/charts/line-chart";
import { QuantTab } from "@/components/stock/quant-tab";
import { WhaleTab } from "@/components/stock/whale-tab";
import { FundamentalsTab } from "@/components/stock/fundamentals-tab";
import { CompositeTab } from "@/components/stock/composite-tab";
import { SimulationTab } from "@/components/stock/simulation-tab";
import { NewsTab } from "@/components/stock/news-tab";
import { cn, formatKRW, formatPercent, formatLargeNumber } from "@/lib/utils";
import { useState, useMemo } from "react";

type TabType = "price" | "quant" | "whale" | "fundamental" | "composite" | "simulation" | "news";

type PeriodType = "1M" | "3M" | "6M" | "1Y" | "ALL";

const PERIOD_DAYS: Record<PeriodType, number | null> = {
  "1M": 30,
  "3M": 90,
  "6M": 180,
  "1Y": 365,
  "ALL": null,
};

export default function StockDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const ticker = params.ticker as string;
  const activeTab = (searchParams.get("tab") || "composite") as TabType;

  const [period, setPeriod] = useState<PeriodType>("3M");

  // Calculate date range
  const { startDate, endDate } = useMemo(() => {
    const days = PERIOD_DAYS[period];
    const end = new Date().toISOString().split("T")[0];
    if (!days) return { startDate: undefined, endDate: end };
    const start = new Date();
    start.setDate(start.getDate() - days);
    return { startDate: start.toISOString().split("T")[0], endDate: end };
  }, [period]);

  // Fetch data
  const { data: stockData, isLoading: stockLoading, error: stockError } = useStockDetail(ticker);
  const { data: priceData, isLoading: priceLoading } = usePriceHistory(ticker, startDate, endDate);
  const { data: investorData, isLoading: investorLoading } = useInvestorHistory(ticker, startDate, endDate);

  const setTab = (tab: TabType) => {
    router.push(`/stocks/${ticker}?tab=${tab}`);
  };

  // Loading state
  if (stockLoading) {
    return (
      <div className="max-w-7xl mx-auto p-6 space-y-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-slate-200 rounded w-1/3"></div>
          <div className="h-12 bg-slate-200 rounded w-1/2"></div>
          <div className="h-96 bg-slate-200 rounded"></div>
        </div>
      </div>
    );
  }

  // Error state
  if (stockError || !stockData) {
    return (
      <div className="max-w-7xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          <h2 className="font-semibold mb-2">데이터를 불러올 수 없습니다</h2>
          <p className="text-sm">종목 정보를 가져오는 중 오류가 발생했습니다.</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 text-sm"
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  const stock = stockData.data;
  const prices = priceData?.data || [];
  const investors = investorData?.data || [];

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Stock Header */}
      <header className="space-y-2">
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold text-slate-900">{stock.name}</h1>
          <span className="text-lg text-slate-500">{stock.ticker}</span>
          <span
            className={cn(
              "px-2.5 py-0.5 rounded-full text-xs font-medium",
              stock.market === "KOSPI"
                ? "bg-blue-100 text-blue-800"
                : "bg-purple-100 text-purple-800"
            )}
          >
            {stock.market}
          </span>
          {!stock.is_active && (
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
              상장폐지
            </span>
          )}
        </div>
        {stock.sector && (
          <p className="text-sm text-slate-600">업종: {stock.sector}</p>
        )}
        {stock.latest_price && (
          <div className="flex items-baseline gap-4">
            <span className="text-3xl font-semibold text-slate-900">
              {formatKRW(stock.latest_price.close)}원
            </span>
            {stock.latest_price.change_rate !== null && (
              <span
                className={cn(
                  "text-lg font-medium",
                  stock.latest_price.change_rate > 0
                    ? "text-red-600"
                    : stock.latest_price.change_rate < 0
                      ? "text-blue-600"
                      : "text-slate-600"
                )}
              >
                {formatPercent(stock.latest_price.change_rate)}
              </span>
            )}
          </div>
        )}
      </header>

      {/* Tab Navigation */}
      <nav className="border-b border-slate-200">
        <div className="flex gap-8">
          {[
            { key: "composite", label: "종합(WCS)" },
            { key: "price", label: "가격" },
            { key: "quant", label: "퀀트" },
            { key: "whale", label: "수급" },
            { key: "fundamental", label: "펀더멘털" },
            { key: "simulation", label: "시뮬레이션" },
            { key: "news", label: "뉴스감성" },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setTab(tab.key as TabType)}
              className={cn(
                "pb-3 px-1 font-medium text-sm border-b-2 transition-colors",
                activeTab === tab.key
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      {/* Tab Content */}
      {activeTab === "composite" && <CompositeTab ticker={ticker} />}

      {activeTab === "price" && (
        <div className="space-y-6">
          {/* Period Selector */}
          <div className="flex justify-end gap-2">
            {(["1M", "3M", "6M", "1Y", "ALL"] as PeriodType[]).map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={cn(
                  "px-3 py-1.5 text-sm font-medium rounded transition-colors",
                  period === p
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                )}
              >
                {p === "ALL" ? "전체" : p}
              </button>
            ))}
          </div>

          {/* Price Chart */}
          <div className="bg-white rounded-lg border border-slate-200 p-6 space-y-4">
            <h2 className="text-lg font-semibold text-slate-900">주가 차트</h2>
            {priceLoading ? (
              <div className="animate-pulse h-96 bg-slate-100 rounded"></div>
            ) : prices.length > 0 ? (
              <CandlestickChart data={prices} height={450} />
            ) : (
              <div className="flex items-center justify-center h-96 text-slate-400">
                선택한 기간의 데이터가 없습니다
              </div>
            )}
          </div>

          {/* Key Stats */}
          {stock.latest_price && (
            <div className="bg-white rounded-lg border border-slate-200 p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">주요 지표</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                <div>
                  <p className="text-sm text-slate-600 mb-1">시가</p>
                  <p className="text-lg font-semibold text-slate-900">
                    {formatKRW(stock.latest_price.open)}원
                  </p>
                </div>
                <div>
                  <p className="text-sm text-slate-600 mb-1">고가</p>
                  <p className="text-lg font-semibold text-red-600">
                    {formatKRW(stock.latest_price.high)}원
                  </p>
                </div>
                <div>
                  <p className="text-sm text-slate-600 mb-1">저가</p>
                  <p className="text-lg font-semibold text-blue-600">
                    {formatKRW(stock.latest_price.low)}원
                  </p>
                </div>
                <div>
                  <p className="text-sm text-slate-600 mb-1">종가</p>
                  <p className="text-lg font-semibold text-slate-900">
                    {formatKRW(stock.latest_price.close)}원
                  </p>
                </div>
                <div>
                  <p className="text-sm text-slate-600 mb-1">거래량</p>
                  <p className="text-lg font-semibold text-slate-900">
                    {formatLargeNumber(stock.latest_price.volume)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-slate-600 mb-1">거래대금</p>
                  <p className="text-lg font-semibold text-slate-900">
                    {formatLargeNumber(stock.latest_price.trading_value)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-slate-600 mb-1">전일대비</p>
                  <p
                    className={cn(
                      "text-lg font-semibold",
                      stock.latest_price.change_rate && stock.latest_price.change_rate > 0
                        ? "text-red-600"
                        : stock.latest_price.change_rate && stock.latest_price.change_rate < 0
                          ? "text-blue-600"
                          : "text-slate-900"
                    )}
                  >
                    {formatPercent(stock.latest_price.change_rate)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-slate-600 mb-1">기준일</p>
                  <p className="text-lg font-semibold text-slate-900">
                    {stock.latest_price.trade_date}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Investor Flow Chart */}
          <div className="bg-white rounded-lg border border-slate-200 p-6 space-y-4">
            <h2 className="text-lg font-semibold text-slate-900">투자자별 수급</h2>
            {investorLoading ? (
              <div className="animate-pulse h-80 bg-slate-100 rounded"></div>
            ) : investors.length > 0 ? (
              <LineChart
                series={[
                  {
                    name: "기관",
                    data: investors.map((d: typeof investors[0]) => d.institution_net || 0),
                    color: "#3b82f6",
                  },
                  {
                    name: "외국인",
                    data: investors.map((d: typeof investors[0]) => d.foreign_net || 0),
                    color: "#10b981",
                  },
                  {
                    name: "연기금",
                    data: investors.map((d: typeof investors[0]) => d.pension_net || 0),
                    color: "#f59e0b",
                  },
                ]}
                xLabels={investors.map((d: typeof investors[0]) => d.trade_date)}
                height={350}
                yAxisName="순매수 (주)"
              />
            ) : (
              <div className="flex items-center justify-center h-80 text-slate-400">
                선택한 기간의 수급 데이터가 없습니다
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === "quant" && <QuantTab ticker={ticker} />}

      {activeTab === "whale" && <WhaleTab ticker={ticker} />}

      {activeTab === "fundamental" && <FundamentalsTab ticker={ticker} />}

      {activeTab === "simulation" && <SimulationTab ticker={ticker} />}

      {activeTab === "news" && <NewsTab ticker={ticker} />}
    </div>
  );
}
