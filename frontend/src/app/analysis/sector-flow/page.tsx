"use client";

import { useSectorFlowOverview, useSectorFlowHeatmap } from "@/lib/queries";
import { cn, formatLargeNumber } from "@/lib/utils";
import { useState } from "react";
import ReactECharts from "echarts-for-react";
import Link from "next/link";
import type { SectorFlowOverviewItem, SectorFlowHeatmapData } from "@/types/api";

const investorTypeLabels: Record<string, string> = {
  institution_net: "기관",
  foreign_net: "외국인",
  pension_net: "연기금",
  private_equity_net: "사모펀드",
  other_corp_net: "기타법인",
};

const signalColors: Record<string, { bg: string; text: string }> = {
  strong_accumulation: { bg: "bg-emerald-100", text: "text-emerald-800" },
  mild_accumulation: { bg: "bg-blue-100", text: "text-blue-800" },
  neutral: { bg: "bg-gray-100", text: "text-gray-600" },
  distribution: { bg: "bg-orange-100", text: "text-orange-800" },
};

const signalLabels: Record<string, string> = {
  strong_accumulation: "강한 매집",
  mild_accumulation: "매집",
  neutral: "중립",
  distribution: "매도",
};

type MetricType = "intensity" | "consistency" | "net_purchase";

export default function SectorFlowPage() {
  const [metric, setMetric] = useState<MetricType>("intensity");
  const { data: overviewData, isLoading: overviewLoading } = useSectorFlowOverview();
  const { data: heatmapData, isLoading: heatmapLoading } = useSectorFlowHeatmap(metric);

  const overview: SectorFlowOverviewItem[] = overviewData?.data || [];
  const heatmap: SectorFlowHeatmapData | null = heatmapData?.data || null;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">섹터 수급 분석</h1>
        <p className="text-slate-500 mt-1">섹터별 고래 투자자 순매수 흐름 분석</p>
      </div>

      {/* Heatmap Section */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-900">섹터 × 고래 히트맵</h2>
          <div className="flex gap-2">
            {([
              { key: "intensity", label: "강도" },
              { key: "consistency", label: "일관성" },
              { key: "net_purchase", label: "순매수" },
            ] as { key: MetricType; label: string }[]).map((m) => (
              <button
                key={m.key}
                onClick={() => setMetric(m.key)}
                className={cn(
                  "px-3 py-1.5 text-sm font-medium rounded transition-colors",
                  metric === m.key
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                )}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>

        {heatmapLoading ? (
          <div className="h-96 bg-slate-100 animate-pulse rounded" />
        ) : heatmap && heatmap.sectors.length > 0 ? (
          <HeatmapChart heatmap={heatmap} metric={metric} />
        ) : (
          <div className="h-96 flex items-center justify-center text-slate-400">
            히트맵 데이터가 없습니다
          </div>
        )}
      </div>

      {/* Sector Overview Table */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">섹터별 수급 현황</h2>
        {overviewLoading ? (
          <div className="h-64 bg-slate-100 animate-pulse rounded" />
        ) : overview.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 border-b">
                  <th className="text-left py-2 px-2">섹터</th>
                  {Object.values(investorTypeLabels).map((label) => (
                    <th key={label} className="text-center py-2 px-2">{label}</th>
                  ))}
                  <th className="text-center py-2 px-2">종합 신호</th>
                </tr>
              </thead>
              <tbody>
                {overview.map((item) => (
                  <tr key={item.sector} className="border-b border-slate-50 hover:bg-slate-50">
                    <td className="py-2 px-2 font-medium">{item.sector}</td>
                    {Object.keys(investorTypeLabels).map((type) => {
                      const flow = item.flows?.[type];
                      const signal = flow?.signal || "neutral";
                      const sc = signalColors[signal] || signalColors.neutral;
                      return (
                        <td key={type} className="text-center py-2 px-2">
                          <span className={cn("inline-block px-2 py-0.5 rounded text-xs", sc.bg, sc.text)}>
                            {signalLabels[signal] || "중립"}
                          </span>
                        </td>
                      );
                    })}
                    <td className="text-center py-2 px-2">
                      {item.dominant_signal ? (
                        <span className={cn(
                          "inline-block px-2 py-0.5 rounded text-xs font-semibold",
                          signalColors[item.dominant_signal]?.bg || "bg-gray-100",
                          signalColors[item.dominant_signal]?.text || "text-gray-600"
                        )}>
                          {signalLabels[item.dominant_signal] || item.dominant_signal}
                        </span>
                      ) : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="h-32 flex items-center justify-center text-slate-400">
            섹터 수급 데이터가 없습니다
          </div>
        )}
      </div>

      {/* Methodology */}
      <div className="bg-slate-50 rounded-lg border border-slate-200 p-6">
        <h3 className="text-sm font-semibold text-slate-800 mb-2">섹터 수급 분석이란?</h3>
        <div className="text-sm text-slate-600 space-y-2">
          <p>
            각 섹터(업종)별로 5대 고래 투자자(기관, 외국인, 연기금, 사모펀드, 기타법인)의 순매수 흐름을 분석하여
            어떤 섹터에 자금이 유입/유출되고 있는지 한눈에 보여줍니다.
          </p>
          <ul className="list-disc list-inside space-y-1 text-xs">
            <li><strong>강도(Intensity):</strong> 순매수 규모 / 섹터 전체 거래대금</li>
            <li><strong>일관성(Consistency):</strong> 순매수 방향이 일관된 일수 비율</li>
            <li><strong>신호:</strong> 강도와 일관성을 종합하여 매집/중립/매도 판단</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

function HeatmapChart({ heatmap, metric }: { heatmap: SectorFlowHeatmapData; metric: MetricType }) {
  const metricLabel = metric === "intensity" ? "강도" : metric === "consistency" ? "일관성" : "순매수";

  // Build data array for ECharts: [xIndex, yIndex, value]
  const data: [number, number, number][] = [];
  const { sectors, investor_types, matrix } = heatmap;

  for (let y = 0; y < sectors.length; y++) {
    for (let x = 0; x < investor_types.length; x++) {
      const val = matrix[y]?.[x] ?? 0;
      data.push([x, y, val]);
    }
  }

  const investorLabels = investor_types.map((t) => investorTypeLabels[t] || t);

  // Determine min/max and color scheme per metric
  const values = data.map(([, , v]) => v);

  let minVal: number, maxVal: number;
  let colors: string[];
  let formatTip: (val: number) => string;

  if (metric === "net_purchase") {
    // Diverging: symmetric around 0
    const absMax = Math.max(...values.map(Math.abs), 1);
    minVal = -absMax;
    maxVal = absMax;
    colors = ["#ef4444", "#fbbf24", "#f5f5f5", "#86efac", "#10b981"];
    formatTip = (val) => formatLargeNumber(val);
  } else if (metric === "consistency") {
    // Diverging: 0 (always sell) → 0.5 (neutral) → 1 (always buy)
    minVal = 0;
    maxVal = 1;
    colors = ["#ef4444", "#fbbf24", "#f5f5f5", "#86efac", "#10b981"];
    formatTip = (val) => `${(val * 100).toFixed(0)}%`;
  } else {
    // Intensity: magnitude only, no direction → single-color gradient
    minVal = 0;
    maxVal = Math.max(...values, 0.001);
    colors = ["#f5f5f5", "#c4b5fd", "#8b5cf6", "#6d28d9"];
    formatTip = (val) => `${(val * 100).toFixed(2)}%`;
  }

  const option = {
    tooltip: {
      position: "top",
      formatter: (params: any) => {
        const investorLabel = investorLabels[params.data[0]];
        const sector = sectors[params.data[1]];
        return `${sector}<br/>${investorLabel}: ${formatTip(params.data[2])}`;
      },
    },
    grid: { left: "12%", right: "8%", top: "8%", bottom: "18%" },
    xAxis: {
      type: "category",
      data: investorLabels,
      axisLabel: { fontSize: 11 },
      splitArea: { show: true },
    },
    yAxis: {
      type: "category",
      data: sectors,
      axisLabel: { fontSize: 10, interval: 0 },
      splitArea: { show: true },
    },
    visualMap: {
      min: minVal,
      max: maxVal,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: "0%",
      inRange: { color: colors },
      textStyle: { fontSize: 10 },
    },
    series: [
      {
        type: "heatmap",
        data,
        label: { show: false },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: "rgba(0, 0, 0, 0.5)" },
        },
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: 400 }} />;
}
