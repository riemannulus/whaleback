"use client";

import { Suspense, useMemo } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useQuantRankings } from "@/lib/queries";
import { BarChart } from "@/components/charts";
import { cn, formatKRW, formatPercent } from "@/lib/utils";

const MARKETS = ["전체", "KOSPI", "KOSDAQ"] as const;
const GRADES = ["전체", "A+", "A", "B+", "B", "C+", "C", "D", "F"] as const;
const MIN_FSCORES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] as const;

function getGradeColor(grade: string | null): string {
  if (!grade) return "bg-gray-100 text-gray-600";
  const g = grade.toUpperCase();
  if (g.startsWith("A")) return "bg-green-100 text-green-700";
  if (g.startsWith("B")) return "bg-blue-100 text-blue-700";
  if (g.startsWith("C")) return "bg-yellow-100 text-yellow-700";
  if (g === "D") return "bg-orange-100 text-orange-700";
  if (g === "F") return "bg-red-100 text-red-700";
  return "bg-gray-100 text-gray-600";
}

function getSafetyMarginColor(margin: number | null): string {
  if (margin == null) return "text-gray-400";
  if (margin > 20) return "text-green-600 font-semibold";
  if (margin > 0) return "text-yellow-600";
  return "text-red-600";
}

function QuantAnalysisContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const market = searchParams.get("market") || "전체";
  const grade = searchParams.get("grade") || "전체";
  const minFScore = parseInt(searchParams.get("min_fscore") || "0", 10);
  const page = parseInt(searchParams.get("page") || "1", 10);

  const updateParams = (updates: Record<string, string | null>) => {
    const params = new URLSearchParams(searchParams.toString());
    Object.entries(updates).forEach(([key, value]) => {
      if (value === null || value === "전체" || value === "0") {
        params.delete(key);
      } else {
        params.set(key, value);
      }
    });
    router.push(`/analysis/quant?${params.toString()}`);
  };

  const resetFilters = () => {
    router.push("/analysis/quant");
  };

  const queryParams = {
    market: market === "전체" ? undefined : market,
    grade: grade === "전체" ? undefined : grade,
    min_fscore: minFScore === 0 ? undefined : minFScore,
    page,
    size: 20,
  };

  const { data, isLoading, error } = useQuantRankings(queryParams);

  // Grade distribution
  const gradeDistribution = useMemo(() => {
    if (!data?.data) return {};
    const dist: Record<string, number> = {};
    data.data.forEach((item: typeof data.data[0]) => {
      const g = item.investment_grade || "N/A";
      dist[g] = (dist[g] || 0) + 1;
    });
    return dist;
  }, [data]);

  // Top 20 by safety margin
  const top20SafetyMargin = useMemo(() => {
    if (!data?.data) return { labels: [], values: [], colors: [] };
    const sorted = [...data.data]
      .filter((item) => item.safety_margin != null)
      .sort((a, b) => (b.safety_margin || 0) - (a.safety_margin || 0))
      .slice(0, 20);
    return {
      labels: sorted.map((item) => item.name || item.ticker),
      values: sorted.map((item) => item.safety_margin || 0),
      colors: sorted.map((item) =>
        (item.safety_margin || 0) > 0 ? "#10b981" : "#ef4444"
      ),
    };
  }, [data]);

  const totalPages = data?.meta ? Math.ceil(data.meta.total / data.meta.size) : 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900">퀀트 분석</h1>
        <p className="text-slate-600 mt-1">
          RIM 내재가치, F-Score, 투자등급 기반 종목 분석
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 space-y-3">
        <div className="flex flex-wrap gap-4 items-end">
          {/* Market */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              시장
            </label>
            <select
              value={market}
              onChange={(e) => updateParams({ market: e.target.value, page: "1" })}
              className="px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-whale-500"
            >
              {MARKETS.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          {/* Grade */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              투자등급
            </label>
            <select
              value={grade}
              onChange={(e) => updateParams({ grade: e.target.value, page: "1" })}
              className="px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-whale-500"
            >
              {GRADES.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </div>

          {/* Min F-Score */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              최소 F-Score
            </label>
            <select
              value={minFScore}
              onChange={(e) =>
                updateParams({ min_fscore: e.target.value, page: "1" })
              }
              className="px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-whale-500"
            >
              {MIN_FSCORES.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          </div>

          {/* Reset */}
          <button
            onClick={resetFilters}
            className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 border border-slate-300 rounded-md hover:bg-slate-50 transition-colors"
          >
            필터 초기화
          </button>
        </div>
      </div>

      {/* Grade Distribution */}
      {data && Object.keys(gradeDistribution).length > 0 && (
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold text-slate-900 mb-3">
            투자등급 분포
          </h2>
          <div className="flex flex-wrap gap-3">
            {Object.entries(gradeDistribution)
              .sort(([a], [b]) => {
                const order = ["A+", "A", "B+", "B", "C+", "C", "D", "F", "N/A"];
                return order.indexOf(a) - order.indexOf(b);
              })
              .map(([g, count]) => (
                <div
                  key={g}
                  className="flex items-center gap-2 px-3 py-2 bg-slate-50 rounded-md"
                >
                  <span
                    className={cn(
                      "px-2 py-1 rounded text-xs font-semibold",
                      getGradeColor(g)
                    )}
                  >
                    {g}
                  </span>
                  <span className="text-sm text-slate-600">{count}개</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Top 20 Safety Margin Chart */}
      {top20SafetyMargin.labels.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold text-slate-900 mb-3">
            안전마진 상위 20개 종목
          </h2>
          <BarChart
            labels={top20SafetyMargin.labels}
            series={[
              {
                name: "안전마진 (%)",
                data: top20SafetyMargin.values,
              },
            ]}
            height={500}
            horizontal={true}
          />
        </div>
      )}

      {/* Rankings Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">종목 순위</h2>
          {data?.meta && (
            <p className="text-sm text-slate-600 mt-1">
              총 {data.meta.total}개 종목
            </p>
          )}
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="p-8 text-center">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-whale-600 border-r-transparent"></div>
            <p className="mt-2 text-sm text-slate-600">데이터를 불러오는 중...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="p-8 text-center">
            <p className="text-red-600">데이터를 불러오는데 실패했습니다.</p>
          </div>
        )}

        {/* Table */}
        {data && !isLoading && (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">
                      순위
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">
                      종목
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">
                      시장
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 uppercase">
                      내재가치
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 uppercase">
                      안전마진
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">
                      F-Score
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">
                      투자등급
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">
                      데이터완성도
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {data.data.map((item: typeof data.data[0], idx: number) => {
                    const rank = (page - 1) * 20 + idx + 1;
                    return (
                      <tr
                        key={item.ticker}
                        className="hover:bg-slate-50 cursor-pointer transition-colors"
                        onClick={() => router.push(`/stocks/${item.ticker}`)}
                      >
                        <td className="px-4 py-3 text-sm text-slate-900">
                          {rank}
                        </td>
                        <td className="px-4 py-3">
                          <Link
                            href={`/stocks/${item.ticker}`}
                            className="block hover:text-whale-600"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <div className="font-medium text-slate-900">
                              {item.ticker}
                            </div>
                            <div className="text-xs text-slate-500">
                              {item.name || "-"}
                            </div>
                          </Link>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span
                            className={cn(
                              "inline-block px-2 py-1 rounded text-xs font-medium",
                              item.market === "KOSPI"
                                ? "bg-blue-100 text-blue-700"
                                : "bg-purple-100 text-purple-700"
                            )}
                          >
                            {item.market || "-"}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right text-sm text-slate-900">
                          {formatKRW(item.rim_value)}
                        </td>
                        <td
                          className={cn(
                            "px-4 py-3 text-right text-sm",
                            getSafetyMarginColor(item.safety_margin)
                          )}
                        >
                          {item.safety_margin != null
                            ? formatPercent(item.safety_margin)
                            : "-"}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-col items-center gap-1">
                            <span className="text-sm font-medium text-slate-900">
                              {item.fscore != null ? `${item.fscore}/9` : "-"}
                            </span>
                            {item.fscore != null && (
                              <div className="w-full bg-slate-200 rounded-full h-1.5">
                                <div
                                  className="bg-whale-600 h-1.5 rounded-full transition-all"
                                  style={{
                                    width: `${(item.fscore / 9) * 100}%`,
                                  }}
                                />
                              </div>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span
                            className={cn(
                              "inline-block px-2 py-1 rounded text-xs font-semibold",
                              getGradeColor(item.investment_grade)
                            )}
                          >
                            {item.investment_grade || "-"}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-col items-center gap-1">
                            <span className="text-sm text-slate-600">
                              {item.data_completeness != null
                                ? `${Math.round(item.data_completeness * 100)}%`
                                : "-"}
                            </span>
                            {item.data_completeness != null && (
                              <div className="w-full bg-slate-200 rounded-full h-1.5">
                                <div
                                  className={cn(
                                    "h-1.5 rounded-full transition-all",
                                    item.data_completeness >= 0.8
                                      ? "bg-green-500"
                                      : item.data_completeness >= 0.5
                                      ? "bg-yellow-500"
                                      : "bg-red-500"
                                  )}
                                  style={{
                                    width: `${item.data_completeness * 100}%`,
                                  }}
                                />
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="px-4 py-3 border-t border-slate-200 flex items-center justify-between">
                <div className="text-sm text-slate-600">
                  페이지 {page} / {totalPages}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => updateParams({ page: String(page - 1) })}
                    disabled={page <= 1}
                    className="px-3 py-1 text-sm font-medium text-slate-600 border border-slate-300 rounded-md hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    이전
                  </button>
                  <button
                    onClick={() => updateParams({ page: String(page + 1) })}
                    disabled={page >= totalPages}
                    className="px-3 py-1 text-sm font-medium text-slate-600 border border-slate-300 rounded-md hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    다음
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default function QuantAnalysisPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-whale-600 border-r-transparent"></div>
      </div>
    }>
      <QuantAnalysisContent />
    </Suspense>
  );
}
