"use client";

import { useQuantRankings, useWhaleTop, useSectorRanking, usePipelineStatus, useSimulationRankings, useSectorFlowHeatmap } from "@/lib/queries";
import { formatKRW, formatPercent, formatLargeNumber } from "@/lib/utils";
import Link from "next/link";
import ReactECharts from "echarts-for-react";
import type { SectorFlowHeatmapData } from "@/types/api";
import { MarketAISummary } from "@/components/dashboard/market-ai-summary";

function StatCard({ title, value, subtitle }: { title: string; value: string; subtitle?: string }) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-5">
      <h3 className="text-sm font-medium text-slate-500">{title}</h3>
      <p className="text-2xl font-bold text-slate-900 mt-1">{value}</p>
      {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
    </div>
  );
}

function SectionHeader({ title, href }: { title: string; href: string }) {
  return (
    <div className="flex items-center justify-between mb-3">
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      <Link href={href} className="text-sm text-whale-600 hover:text-whale-700">
        더보기 →
      </Link>
    </div>
  );
}

const investorTypeLabels: Record<string, string> = {
  institution_net: "기관",
  foreign_net: "외국인",
  pension_net: "연기금",
  private_equity_net: "사모",
  other_corp_net: "기타법인",
};

function MiniHeatmapChart({ heatmap }: { heatmap: SectorFlowHeatmapData }) {
  const { sectors, investor_types, matrix } = heatmap;
  const data: [number, number, number][] = [];

  for (let y = 0; y < sectors.length; y++) {
    for (let x = 0; x < investor_types.length; x++) {
      data.push([x, y, matrix[y]?.[x] ?? 0]);
    }
  }

  const values = data.map(([, , v]) => v);
  const investorLabels = investor_types.map((t) => investorTypeLabels[t] || t);

  const option = {
    tooltip: {
      position: "top" as const,
      formatter: (params: any) => {
        const investorLabel = investorLabels[params.data[0]];
        const sector = sectors[params.data[1]];
        const val = params.data[2];
        return `${sector}<br/>${investorLabel}: ${(val * 100).toFixed(2)}%`;
      },
    },
    grid: { left: "14%", right: "4%", top: "4%", bottom: "22%" },
    xAxis: {
      type: "category" as const,
      data: investorLabels,
      axisLabel: { fontSize: 10 },
      splitArea: { show: true },
    },
    yAxis: {
      type: "category" as const,
      data: sectors,
      axisLabel: { fontSize: 9, interval: 0 },
      splitArea: { show: true },
    },
    visualMap: {
      min: 0,
      max: Math.max(...values, 0.001),
      calculable: false,
      orient: "horizontal" as const,
      left: "center",
      bottom: "0%",
      itemWidth: 10,
      itemHeight: 80,
      inRange: { color: ["#f5f5f5", "#c4b5fd", "#8b5cf6", "#6d28d9"] },
      textStyle: { fontSize: 9 },
    },
    series: [
      {
        type: "heatmap" as const,
        data,
        label: { show: false },
        emphasis: { itemStyle: { shadowBlur: 6, shadowColor: "rgba(0,0,0,0.3)" } },
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: 220 }} />;
}

export default function DashboardPage() {
  const { data: quantData } = useQuantRankings({ size: 10 });
  const { data: whaleData } = useWhaleTop({ size: 10 });
  const { data: sectorData } = useSectorRanking();
  const { data: pipelineData } = usePipelineStatus();
  const { data: simulationData } = useSimulationRankings({ size: 10 });
  const { data: heatmapData, isLoading: heatmapLoading } = useSectorFlowHeatmap();

  const topStocks = quantData?.data || [];
  const topWhales = whaleData?.data || [];
  const sectors = sectorData?.data || [];
  const collections = pipelineData?.data?.collections || [];
  const topSimulations = simulationData?.data || [];
  const heatmap: SectorFlowHeatmapData | null = heatmapData?.data || null;

  const lastCollection = collections.length > 0
    ? collections.reduce((a: any, b: any) => (a.completed_at > b.completed_at ? a : b))
    : null;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">대시보드</h1>
        <p className="text-slate-500 mt-1">한국 주식 시장 분석 - KOSPI/KOSDAQ</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="분석 종목"
          value={String(quantData?.meta?.total || "-")}
          subtitle="퀀트 분석 완료"
        />
        <StatCard
          title="고래 매집 종목"
          value={String(whaleData?.meta?.total || "-")}
          subtitle="Whale Score 기준"
        />
        <StatCard
          title="추적 섹터"
          value={String(sectors.length || "-")}
          subtitle="KOSPI + KOSDAQ"
        />
        <StatCard
          title="최근 수집"
          value={lastCollection?.target_date || "-"}
          subtitle={lastCollection?.status === "success" ? "성공" : "확인 필요"}
        />
      </div>

      {/* Market AI Summary */}
      <MarketAISummary />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Quant Picks */}
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-5">
          <SectionHeader title="퀀트 분석 TOP 10" href="/analysis/quant" />
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 border-b">
                  <th className="text-left py-2">종목</th>
                  <th className="text-center py-2">등급</th>
                  <th className="text-center py-2">F-Score</th>
                  <th className="text-right py-2">안전마진</th>
                </tr>
              </thead>
              <tbody>
                {topStocks.map((stock: any) => (
                  <tr key={stock.ticker} className="border-b border-slate-50 hover:bg-slate-50">
                    <td className="py-2">
                      <Link href={`/stocks/${stock.ticker}`} className="hover:text-whale-600">
                        <span className="font-medium">{stock.name}</span>
                        <span className="text-slate-400 text-xs ml-1">{stock.ticker}</span>
                      </Link>
                    </td>
                    <td className="text-center">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                        stock.investment_grade?.startsWith("A") ? "bg-green-100 text-green-700" :
                        stock.investment_grade?.startsWith("B") ? "bg-blue-100 text-blue-700" :
                        "bg-slate-100 text-slate-600"
                      }`}>
                        {stock.investment_grade || "-"}
                      </span>
                    </td>
                    <td className="text-center">{stock.fscore ?? "-"}/9</td>
                    <td className="text-right">{formatPercent(stock.safety_margin)}</td>
                  </tr>
                ))}
                {topStocks.length === 0 && (
                  <tr><td colSpan={4} className="py-4 text-center text-slate-400">데이터 없음</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Top Whale Picks */}
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-5">
          <SectionHeader title="고래 매집 TOP 10" href="/analysis/whale" />
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 border-b">
                  <th className="text-left py-2">종목</th>
                  <th className="text-center py-2">신호</th>
                  <th className="text-right py-2">Whale Score</th>
                </tr>
              </thead>
              <tbody>
                {topWhales.map((stock: any) => (
                  <tr key={stock.ticker} className="border-b border-slate-50 hover:bg-slate-50">
                    <td className="py-2">
                      <Link href={`/stocks/${stock.ticker}`} className="hover:text-whale-600">
                        <span className="font-medium">{stock.name}</span>
                        <span className="text-slate-400 text-xs ml-1">{stock.ticker}</span>
                      </Link>
                    </td>
                    <td className="text-center">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs ${
                        stock.signal === "strong_accumulation" ? "bg-red-100 text-red-700" :
                        stock.signal === "mild_accumulation" ? "bg-orange-100 text-orange-700" :
                        "bg-slate-100 text-slate-600"
                      }`}>
                        {stock.signal === "strong_accumulation" ? "강한매집" :
                         stock.signal === "mild_accumulation" ? "완만매집" :
                         stock.signal === "distribution" ? "매도우위" : "중립"}
                      </span>
                    </td>
                    <td className="text-right font-medium">{stock.whale_score?.toFixed(1) ?? "-"}</td>
                  </tr>
                ))}
                {topWhales.length === 0 && (
                  <tr><td colSpan={3} className="py-4 text-center text-slate-400">데이터 없음</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Simulation TOP 10 */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-5">
        <SectionHeader title="시뮬레이션 TOP 10" href="/analysis/sector-flow" />
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-500 border-b">
                <th className="text-left py-2">종목</th>
                <th className="text-center py-2">등급</th>
                <th className="text-right py-2">Sim Score</th>
                <th className="text-right py-2">6M 기대수익</th>
              </tr>
            </thead>
            <tbody>
              {topSimulations.map((stock: any) => (
                <tr key={stock.ticker} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="py-2">
                    <Link href={`/stocks/${stock.ticker}?tab=simulation`} className="hover:text-whale-600">
                      <span className="font-medium">{stock.name}</span>
                      <span className="text-slate-400 text-xs ml-1">{stock.ticker}</span>
                    </Link>
                  </td>
                  <td className="text-center">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                      stock.simulation_grade === "positive" ? "bg-emerald-100 text-emerald-700" :
                      stock.simulation_grade === "neutral_positive" ? "bg-blue-100 text-blue-700" :
                      stock.simulation_grade === "neutral" ? "bg-yellow-100 text-yellow-700" :
                      "bg-red-100 text-red-700"
                    }`}>
                      {stock.simulation_grade === "positive" ? "긍정적" :
                       stock.simulation_grade === "neutral_positive" ? "중립+" :
                       stock.simulation_grade === "neutral" ? "중립" : "부정적"}
                    </span>
                  </td>
                  <td className="text-right font-medium">{stock.simulation_score?.toFixed(1) ?? "-"}</td>
                  <td className="text-right">
                    <span className={stock.expected_return_pct_6m > 0 ? "text-red-600" : "text-blue-600"}>
                      {stock.expected_return_pct_6m != null ? `${stock.expected_return_pct_6m > 0 ? "+" : ""}${stock.expected_return_pct_6m.toFixed(1)}%` : "-"}
                    </span>
                  </td>
                </tr>
              ))}
              {topSimulations.length === 0 && (
                <tr><td colSpan={4} className="py-4 text-center text-slate-400">데이터 없음</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Sector Flow Mini Heatmap */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-5">
        <SectionHeader title="섹터 수급 히트맵" href="/analysis/sector-flow" />
        {heatmapLoading ? (
          <div className="h-48 bg-slate-100 animate-pulse rounded" />
        ) : heatmap && heatmap.sectors.length > 0 ? (
          <MiniHeatmapChart heatmap={heatmap} />
        ) : (
          <div className="h-48 flex items-center justify-center text-slate-400 text-sm">
            히트맵 데이터 없음
          </div>
        )}
      </div>

      {/* Sector Overview */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-5">
        <SectionHeader title="섹터 랭킹" href="/analysis/trend" />
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          {sectors.slice(0, 10).map((sector: any, idx: number) => (
            <Link
              key={sector.sector}
              href={`/analysis/trend`}
              className="p-3 rounded-lg border border-slate-100 hover:border-whale-200 hover:bg-whale-50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">#{idx + 1}</span>
                <span className="text-xs text-slate-400">{sector.stock_count}종목</span>
              </div>
              <p className="font-medium text-sm mt-1 truncate">{sector.sector}</p>
              <p className={`text-xs mt-0.5 ${
                (sector.avg_rs_20d || 0) >= 1 ? "text-red-500" : "text-blue-500"
              }`}>
                RS {sector.avg_rs_20d?.toFixed(3) || "-"}
              </p>
            </Link>
          ))}
          {sectors.length === 0 && (
            <p className="col-span-full text-center text-slate-400 py-4">섹터 데이터 없음</p>
          )}
        </div>
      </div>
    </div>
  );
}
