"use client";

import { Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useWhaleTop } from "@/lib/queries";
import { BarChart } from "@/components/charts";
import { cn, formatLargeNumber } from "@/lib/utils";
import type { WhaleTopItem } from "@/types/api";

const SIGNAL_CONFIG = {
  strong_accumulation: { label: "강한매집", color: "emerald" },
  mild_accumulation: { label: "약한매집", color: "blue" },
  neutral: { label: "중립", color: "gray" },
  distribution: { label: "분산", color: "red" },
} as const;

const MARKET_OPTIONS = [
  { value: "", label: "전체" },
  { value: "KOSPI", label: "KOSPI" },
  { value: "KOSDAQ", label: "KOSDAQ" },
];

const MIN_SCORE_OPTIONS = [
  { value: "0", label: "0점 이상" },
  { value: "30", label: "30점 이상" },
  { value: "50", label: "50점 이상" },
  { value: "70", label: "70점 이상" },
];

const SIGNAL_OPTIONS = [
  { value: "", label: "전체" },
  { value: "strong_accumulation", label: "강한매집" },
  { value: "mild_accumulation", label: "약한매집" },
  { value: "neutral", label: "중립" },
  { value: "distribution", label: "분산(매도)" },
];

function getScoreColor(score: number | null): string {
  if (score == null) return "bg-gray-200";
  if (score >= 70) return "bg-emerald-500";
  if (score >= 50) return "bg-blue-500";
  if (score >= 30) return "bg-yellow-500";
  return "bg-gray-300";
}

function SignalBadge({ signal }: { signal: string | null }) {
  if (!signal) return <span className="text-sm text-gray-400">-</span>;

  const config = SIGNAL_CONFIG[signal as keyof typeof SIGNAL_CONFIG];
  if (!config) return <span className="text-sm text-gray-400">{signal}</span>;

  const colorMap = {
    emerald: "bg-emerald-100 text-emerald-800 border-emerald-200",
    blue: "bg-blue-100 text-blue-800 border-blue-200",
    gray: "bg-gray-100 text-gray-800 border-gray-200",
    red: "bg-red-100 text-red-800 border-red-200",
  };

  return (
    <span className={cn("inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border", colorMap[config.color])}>
      {config.label}
    </span>
  );
}

function WhalePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const market = searchParams.get("market") || "";
  const minScore = searchParams.get("min_score") || "0";
  const signal = searchParams.get("signal") || "";
  const page = parseInt(searchParams.get("page") || "1", 10);

  const { data, isLoading, error } = useWhaleTop({
    market: market || undefined,
    min_score: parseInt(minScore, 10),
    signal: signal || undefined,
    page,
    size: 20,
  });

  const updateParams = (updates: Record<string, string>) => {
    const params = new URLSearchParams(searchParams.toString());
    Object.entries(updates).forEach(([key, value]) => {
      if (value) params.set(key, value);
      else params.delete(key);
    });
    params.delete("page"); // Reset page on filter change
    router.push(`/analysis/whale?${params.toString()}`);
  };

  const resetFilters = () => {
    router.push("/analysis/whale");
  };

  const handlePageChange = (newPage: number) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", newPage.toString());
    router.push(`/analysis/whale?${params.toString()}`);
  };

  // Calculate signal summary
  const signalCounts = data?.data.reduce((acc: Record<string, number>, item: typeof data.data[0]) => {
    const signal = item.signal || "neutral";
    acc[signal] = (acc[signal] || 0) + 1;
    return acc;
  }, {} as Record<string, number>) || {};

  const totalSignalCount = (Object.values(signalCounts) as number[]).reduce((a, b) => a + b, 0);

  // Prepare chart data (top 10)
  const chartData = data?.data.slice(0, 10) || [];
  const chartLabels = chartData.map((item: typeof chartData[0]) => item.name || item.ticker);
  const chartSeries = [
    {
      name: "기관",
      data: chartData.map((item: typeof chartData[0]) => (item.institution_net_20d || 0) / 100000000), // Convert to 억
      color: "#3b82f6", // blue-500
    },
    {
      name: "외국인",
      data: chartData.map((item: typeof chartData[0]) => (item.foreign_net_20d || 0) / 100000000),
      color: "#10b981", // green-500
    },
    {
      name: "연기금",
      data: chartData.map((item: typeof chartData[0]) => (item.pension_net_20d || 0) / 100000000),
      color: "#8b5cf6", // purple-500
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">수급 분석</h1>
        <p className="mt-2 text-sm text-gray-600">기관·외국인·연기금 순매수 추적 및 고래 점수</p>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap gap-3 items-center bg-white p-4 rounded-lg border border-gray-200">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">시장:</label>
          <select
            value={market}
            onChange={(e) => updateParams({ market: e.target.value })}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {MARKET_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">최소 점수:</label>
          <select
            value={minScore}
            onChange={(e) => updateParams({ min_score: e.target.value })}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {MIN_SCORE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">시그널:</label>
          <select
            value={signal}
            onChange={(e) => updateParams({ signal: e.target.value })}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {SIGNAL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <button
          onClick={resetFilters}
          className="ml-auto px-4 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
        >
          초기화
        </button>
      </div>

      {/* Signal Summary Cards */}
      {!isLoading && data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(SIGNAL_CONFIG).map(([key, config]) => {
            const count = signalCounts[key] || 0;
            const colorMap = {
              emerald: "bg-emerald-50 border-emerald-200",
              blue: "bg-blue-50 border-blue-200",
              gray: "bg-gray-50 border-gray-200",
              red: "bg-red-50 border-red-200",
            };
            const textColorMap = {
              emerald: "text-emerald-900",
              blue: "text-blue-900",
              gray: "text-gray-900",
              red: "text-red-900",
            };
            const countColorMap = {
              emerald: "text-emerald-600",
              blue: "text-blue-600",
              gray: "text-gray-600",
              red: "text-red-600",
            };

            return (
              <button
                key={key}
                onClick={() => updateParams({ signal: signal === key ? "" : key })}
                className={cn(
                  "p-4 rounded-lg border text-left transition-all",
                  colorMap[config.color],
                  signal === key && "ring-2 ring-offset-1 ring-blue-500"
                )}
              >
                <div className={cn("text-sm font-medium", textColorMap[config.color])}>{config.label}</div>
                <div className={cn("text-2xl font-bold mt-1", countColorMap[config.color])}>{count}</div>
                <div className="text-xs text-gray-500 mt-0.5">
                  {totalSignalCount > 0 ? `${((count / totalSignalCount) * 100).toFixed(1)}%` : ""}
                </div>
              </button>
            );
          })}
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-20 bg-gray-100 rounded-lg animate-pulse" />
            ))}
          </div>
          <div className="h-96 bg-gray-100 rounded-lg animate-pulse" />
          <div className="h-64 bg-gray-100 rounded-lg animate-pulse" />
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">데이터를 불러오는 중 오류가 발생했습니다.</p>
        </div>
      )}

      {/* Market-wide Flow Chart */}
      {!isLoading && !error && chartData.length > 0 && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">고래 점수 상위 종목별 수급 현황</h2>
          <BarChart
            labels={chartLabels}
            series={chartSeries}
            height={400}
            horizontal={true}
            stacked={true}
          />
          <p className="text-xs text-gray-500 mt-2">* 단위: 억원, 최근 20일 순매수</p>
        </div>
      )}

      {/* Top Picks Table */}
      {!isLoading && !error && data && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider w-16">순위</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">종목</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider w-20">시장</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider w-48">고래점수</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider w-28">시그널</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider w-24">기관 20일</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider w-24">외국인 20일</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider w-24">연기금 20일</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {data.data.map((item: typeof data.data[0], index: number) => {
                  const rank = (page - 1) * 20 + index + 1;
                  const score = item.whale_score || 0;

                  return (
                    <tr
                      key={item.ticker}
                      onClick={() => router.push(`/stocks/${item.ticker}?tab=whale`)}
                      className="hover:bg-gray-50 cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-3 text-sm text-gray-900 font-medium">{rank}</td>
                      <td className="px-4 py-3">
                        <Link
                          href={`/stocks/${item.ticker}?tab=whale`}
                          className="text-sm font-medium text-blue-600 hover:text-blue-800"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {item.ticker}
                        </Link>
                        {item.name && <div className="text-xs text-gray-500">{item.name}</div>}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">{item.market || "-"}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-gray-200 rounded-full h-2 overflow-hidden">
                            <div
                              className={cn("h-full transition-all", getScoreColor(score))}
                              style={{ width: `${score}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium text-gray-900 w-10 text-right">{score.toFixed(0)}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <SignalBadge signal={item.signal} />
                      </td>
                      <td className="px-4 py-3 text-sm text-right">
                        <span className={cn(
                          "font-medium",
                          (item.institution_net_20d || 0) > 0 ? "text-red-600" : (item.institution_net_20d || 0) < 0 ? "text-blue-600" : "text-gray-600"
                        )}>
                          {formatLargeNumber(item.institution_net_20d)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-right">
                        <span className={cn(
                          "font-medium",
                          (item.foreign_net_20d || 0) > 0 ? "text-red-600" : (item.foreign_net_20d || 0) < 0 ? "text-blue-600" : "text-gray-600"
                        )}>
                          {formatLargeNumber(item.foreign_net_20d)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-right">
                        <span className={cn(
                          "font-medium",
                          (item.pension_net_20d || 0) > 0 ? "text-red-600" : (item.pension_net_20d || 0) < 0 ? "text-blue-600" : "text-gray-600"
                        )}>
                          {formatLargeNumber(item.pension_net_20d)}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data.meta.total > 20 && (
            <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
              <div className="text-sm text-gray-700">
                전체 {data.meta.total}개 중 {(page - 1) * 20 + 1}-{Math.min(page * 20, data.meta.total)}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handlePageChange(page - 1)}
                  disabled={page === 1}
                  className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  이전
                </button>
                <button
                  onClick={() => handlePageChange(page + 1)}
                  disabled={page * 20 >= data.meta.total}
                  className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  다음
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && data && data.data.length === 0 && (
        <div className="bg-white p-12 rounded-lg border border-gray-200 text-center">
          <p className="text-gray-600">조건에 맞는 종목이 없습니다.</p>
          <button
            onClick={resetFilters}
            className="mt-4 px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-800"
          >
            필터 초기화
          </button>
        </div>
      )}
    </div>
  );
}

export default function WhalePage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-whale-600 border-r-transparent"></div>
      </div>
    }>
      <WhalePageContent />
    </Suspense>
  );
}
