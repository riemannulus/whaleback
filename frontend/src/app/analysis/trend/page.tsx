"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import ReactECharts from "echarts-for-react";
import { useSectorRanking, useSectorRotation, useRelativeStrength } from "@/lib/queries";
import { LineChart } from "@/components/charts/line-chart";
import { cn, formatPercent } from "@/lib/utils";
import type { SectorRankingItem } from "@/types/api";

function TrendAnalysisContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const market = searchParams.get("market") || "all";

  const [rsLookupTicker, setRsLookupTicker] = useState("");
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  // Fetch data
  const { data: rankingData, isLoading: rankingLoading, error: rankingError } = useSectorRanking(
    market === "all" ? undefined : { market }
  );
  const { data: rotationData, isLoading: rotationLoading } = useSectorRotation(
    market === "all" ? undefined : { market }
  );
  const { data: rsData, isLoading: rsLoading } = useRelativeStrength(
    selectedTicker || "",
    "KOSPI"
  );

  const handleMarketChange = (newMarket: string) => {
    const params = new URLSearchParams(searchParams);
    if (newMarket === "all") {
      params.delete("market");
    } else {
      params.set("market", newMarket);
    }
    router.push(`/analysis/trend?${params.toString()}`);
  };

  const handleRsLookup = (e: React.FormEvent) => {
    e.preventDefault();
    if (rsLookupTicker.trim()) {
      setSelectedTicker(rsLookupTicker.trim().toUpperCase());
    }
  };

  const getQuadrantColor = (quadrant: string | null) => {
    switch (quadrant) {
      case "leading": return "bg-emerald-100 text-emerald-800 border-emerald-300";
      case "weakening": return "bg-yellow-100 text-yellow-800 border-yellow-300";
      case "lagging": return "bg-red-100 text-red-800 border-red-300";
      case "improving": return "bg-blue-100 text-blue-800 border-blue-300";
      default: return "bg-gray-100 text-gray-600 border-gray-300";
    }
  };

  const getQuadrantLabel = (quadrant: string | null) => {
    switch (quadrant) {
      case "leading": return "선도";
      case "weakening": return "약화";
      case "lagging": return "지연";
      case "improving": return "회복";
      default: return "-";
    }
  };

  // Prepare scatter chart data
  const scatterChartOption = rotationData ? (() => {
    const sectors = rotationData.data;

    // Calculate median momentum_rank for quadrant divider
    const ranks = sectors
      .map((s: SectorRankingItem) => s.momentum_rank)
      .filter((r: number | null): r is number => r !== null)
      .sort((a: number, b: number) => a - b);
    const medianRank = ranks.length > 0 ? ranks[Math.floor(ranks.length / 2)] : 5;

    const quadrantColorMap: Record<string, string> = {
      leading: "#10b981",
      weakening: "#eab308",
      lagging: "#ef4444",
      improving: "#3b82f6",
    };

    const scatterData = sectors.map((s: SectorRankingItem) => ({
      value: [s.avg_rs_percentile || 50, s.momentum_rank || 5],
      name: s.sector,
      itemStyle: { color: quadrantColorMap[s.quadrant || ""] || "#9ca3af" },
    }));

    return {
      tooltip: {
        trigger: "item",
        formatter: (params: any) => {
          const [rsPercentile, momentumRank] = params.value;
          return `<b>${params.name}</b><br/>RS 백분위: ${rsPercentile?.toFixed(1) || "-"}<br/>모멘텀 순위: ${momentumRank || "-"}`;
        },
      },
      grid: { left: "10%", right: "5%", top: "8%", bottom: "10%" },
      xAxis: {
        type: "value",
        name: "RS 수준 (백분위)",
        nameLocation: "middle",
        nameGap: 25,
        min: 0,
        max: 100,
        axisLine: { show: true },
        splitLine: { show: true, lineStyle: { color: "#f1f5f9" } },
      },
      yAxis: {
        type: "value",
        name: "모멘텀 (순위)",
        nameLocation: "middle",
        nameGap: 40,
        inverse: true,
        axisLine: { show: true },
        splitLine: { show: true, lineStyle: { color: "#f1f5f9" } },
      },
      series: [
        {
          type: "scatter",
          data: scatterData,
          symbolSize: 12,
          label: {
            show: true,
            position: "top",
            formatter: (params: any) => params.name,
            fontSize: 10,
          },
        },
        // Quadrant dividers
        {
          type: "line",
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: { color: "#cbd5e1", width: 1, type: "dashed" },
            data: [
              { xAxis: 50 },
              { yAxis: medianRank },
            ],
          },
        },
      ],
    };
  })() : null;

  // Prepare RS comparison chart data
  const rsChartSeries = rsData ? [
    {
      name: `${rsData.data.ticker} (주식)`,
      data: rsData.data.series.map((p: { stock_indexed: number }) => p.stock_indexed),
      color: "#3b82f6",
    },
    {
      name: `${rsData.data.benchmark} (벤치마크)`,
      data: rsData.data.series.map((p: { index_indexed: number }) => p.index_indexed),
      color: "#94a3b8",
    },
  ] : [];

  const rsChartLabels = rsData ? rsData.data.series.map((p: { date?: string }) => p.date || "") : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">추세 분석</h1>
        <p className="text-muted-foreground mt-1">
          섹터 로테이션, 상대강도, 업종별 트렌드 분석
        </p>
      </div>

      {/* Market Filter */}
      <div className="flex gap-2">
        {["all", "KOSPI", "KOSDAQ"].map((m) => (
          <button
            key={m}
            onClick={() => handleMarketChange(m)}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
              market === m
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            )}
          >
            {m === "all" ? "전체" : m}
          </button>
        ))}
      </div>

      {/* Sector Ranking Table */}
      <div className="bg-white rounded-lg border p-6">
        <h2 className="text-xl font-semibold mb-4">섹터 랭킹</h2>

        {rankingLoading && (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-12 bg-gray-100 rounded animate-pulse" />
            ))}
          </div>
        )}

        {rankingError && (
          <div className="text-red-600 text-sm">데이터를 불러오는 중 오류가 발생했습니다.</div>
        )}

        {rankingData && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-2 font-medium">순위</th>
                  <th className="text-left py-3 px-2 font-medium">섹터</th>
                  <th className="text-right py-3 px-2 font-medium">종목수</th>
                  <th className="text-left py-3 px-2 font-medium">평균 RS 백분위</th>
                  <th className="text-right py-3 px-2 font-medium">평균 RS 20일</th>
                  <th className="text-right py-3 px-2 font-medium">모멘텀</th>
                  <th className="text-center py-3 px-2 font-medium">사분면</th>
                </tr>
              </thead>
              <tbody>
                {rankingData.data
                  .sort((a: SectorRankingItem, b: SectorRankingItem) => (b.avg_rs_percentile || 0) - (a.avg_rs_percentile || 0))
                  .map((sector: SectorRankingItem, idx: number) => (
                    <tr key={sector.sector} className="border-b hover:bg-gray-50">
                      <td className="py-3 px-2 text-gray-600">{idx + 1}</td>
                      <td className="py-3 px-2 font-medium">{sector.sector}</td>
                      <td className="py-3 px-2 text-right">{sector.stock_count}</td>
                      <td className="py-3 px-2">
                        {sector.avg_rs_percentile !== null ? (
                          <div className="flex items-center gap-2">
                            <div className="flex-1 bg-gray-100 rounded-full h-2 max-w-[120px]">
                              <div
                                className="bg-blue-500 h-2 rounded-full"
                                style={{ width: `${sector.avg_rs_percentile}%` }}
                              />
                            </div>
                            <span className="text-xs text-gray-600 w-10 text-right">
                              {sector.avg_rs_percentile.toFixed(0)}
                            </span>
                          </div>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="py-3 px-2 text-right">
                        {sector.avg_rs_20d !== null ? (
                          <span
                            className={cn(
                              "font-medium",
                              sector.avg_rs_20d > 0 && "text-red-600",
                              sector.avg_rs_20d < 0 && "text-blue-600"
                            )}
                          >
                            {formatPercent(sector.avg_rs_20d, 1)}
                          </span>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="py-3 px-2 text-right">
                        {sector.momentum_rank !== null ? (
                          <span className="text-gray-700">{sector.momentum_rank}</span>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="py-3 px-2 text-center">
                        <span
                          className={cn(
                            "inline-block px-2 py-1 rounded text-xs font-medium border",
                            getQuadrantColor(sector.quadrant)
                          )}
                        >
                          {getQuadrantLabel(sector.quadrant)}
                        </span>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Sector Rotation Quadrant Chart */}
      <div className="bg-white rounded-lg border p-6">
        <h2 className="text-xl font-semibold mb-4">섹터 로테이션 사분면</h2>

        {rotationLoading && (
          <div className="h-[400px] bg-gray-100 rounded animate-pulse" />
        )}

        {rotationData && scatterChartOption && (
          <div>
            <ReactECharts option={scatterChartOption} style={{ height: "400px" }} />
            <div className="mt-4 flex justify-center gap-6 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-emerald-500" />
                <span>선도 (Leading)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-yellow-500" />
                <span>약화 (Weakening)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <span>지연 (Lagging)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-500" />
                <span>회복 (Improving)</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* RS Comparison Tool */}
      <div className="bg-white rounded-lg border p-6">
        <h2 className="text-xl font-semibold mb-4">상대강도 비교</h2>

        <form onSubmit={handleRsLookup} className="mb-4">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="종목 코드 입력 (예: 005930)"
              value={rsLookupTicker}
              onChange={(e) => setRsLookupTicker(e.target.value)}
              className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              조회
            </button>
          </div>
        </form>

        {rsLoading && (
          <div className="h-[300px] bg-gray-100 rounded animate-pulse" />
        )}

        {rsData && (
          <div>
            <div className="mb-4 flex gap-6 text-sm">
              <div>
                <span className="text-gray-600">종목:</span>{" "}
                <span className="font-medium">{rsData.data.name || rsData.data.ticker}</span>
              </div>
              <div>
                <span className="text-gray-600">현재 RS 비율:</span>{" "}
                <span className="font-medium">
                  {rsData.data.current_rs !== null ? rsData.data.current_rs.toFixed(2) : "-"}
                </span>
              </div>
              <div>
                <span className="text-gray-600">RS 백분위:</span>{" "}
                <span className="font-medium">
                  {rsData.data.rs_percentile !== null ? `${rsData.data.rs_percentile.toFixed(0)}%` : "-"}
                </span>
              </div>
              <div>
                <span className="text-gray-600">변화율:</span>{" "}
                <span
                  className={cn(
                    "font-medium",
                    rsData.data.rs_change_pct && rsData.data.rs_change_pct > 0 && "text-red-600",
                    rsData.data.rs_change_pct && rsData.data.rs_change_pct < 0 && "text-blue-600"
                  )}
                >
                  {rsData.data.rs_change_pct !== null ? formatPercent(rsData.data.rs_change_pct, 1) : "-"}
                </span>
              </div>
            </div>

            <LineChart
              series={rsChartSeries}
              xLabels={rsChartLabels}
              height={300}
              yAxisName="지수화 가격 (100 기준)"
            />
          </div>
        )}

        {selectedTicker && !rsLoading && !rsData && (
          <div className="text-gray-600 text-sm">해당 종목의 데이터를 찾을 수 없습니다.</div>
        )}
      </div>
    </div>
  );
}

export default function TrendAnalysisPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-whale-600 border-r-transparent"></div>
      </div>
    }>
      <TrendAnalysisContent />
    </Suspense>
  );
}
