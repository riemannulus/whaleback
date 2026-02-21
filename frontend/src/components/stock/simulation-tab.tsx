"use client";

import { useSimulationResult } from "@/lib/queries";
import { GaugeChart } from "@/components/charts/gauge-chart";
import { cn, formatKRW } from "@/lib/utils";
import { AlertCircle, Target } from "lucide-react";
import ReactECharts from "echarts-for-react";
import type { SimulationResult, SimulationHorizon } from "@/types/api";

interface SimulationTabProps {
  ticker: string;
}

const gradeColors: Record<string, { bg: string; text: string; border: string }> = {
  positive: { bg: "bg-emerald-100", text: "text-emerald-800", border: "border-emerald-300" },
  neutral_positive: { bg: "bg-blue-100", text: "text-blue-800", border: "border-blue-300" },
  neutral: { bg: "bg-yellow-100", text: "text-yellow-800", border: "border-yellow-300" },
  negative: { bg: "bg-red-100", text: "text-red-800", border: "border-red-300" },
};

const gradeLabels: Record<string, string> = {
  positive: "긍정적",
  neutral_positive: "중립 긍정",
  neutral: "중립",
  negative: "부정적",
};

export function SimulationTab({ ticker }: SimulationTabProps) {
  const { data, isLoading, error } = useSimulationResult(ticker);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-48 bg-slate-100 animate-pulse rounded-lg" />
        <div className="h-96 bg-slate-100 animate-pulse rounded-lg" />
      </div>
    );
  }

  if (error || !data?.data) {
    return (
      <div className="flex items-center gap-2 text-amber-600 p-6">
        <AlertCircle className="w-5 h-5" />
        <span>시뮬레이션 데이터를 불러올 수 없습니다. (최소 60일 이상의 가격 데이터 필요)</span>
      </div>
    );
  }

  const sim: SimulationResult = data.data;
  const horizons = sim.horizons || {};
  const grade = gradeColors[sim.simulation_grade || "neutral"] || gradeColors.neutral;

  return (
    <div className="space-y-6">
      {/* Simulation Score Card */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">몬테카를로 시뮬레이션</h3>
        <div className="flex flex-col md:flex-row items-center gap-8">
          <div className="flex flex-col items-center">
            <GaugeChart
              value={sim.simulation_score ?? 0}
              max={100}
              label={sim.simulation_score != null ? `${sim.simulation_score.toFixed(1)}` : "N/A"}
              color={
                (sim.simulation_score ?? 0) >= 70 ? "#10b981" :
                (sim.simulation_score ?? 0) >= 50 ? "#3b82f6" :
                (sim.simulation_score ?? 0) >= 30 ? "#eab308" : "#ef4444"
              }
              height={200}
            />
          </div>
          <div className="flex-1 space-y-3">
            <div className="flex items-center gap-3">
              <span className={cn("px-3 py-1 rounded-md border font-semibold text-sm", grade.bg, grade.text, grade.border)}>
                {gradeLabels[sim.simulation_grade || ""] || "분석 불가"}
              </span>
              <span className="text-sm text-slate-500">
                기준가: {sim.base_price != null ? formatKRW(sim.base_price) + "원" : "N/A"}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-slate-500">연간 기대수익률 (μ)</span>
                <div className="font-medium">{sim.mu != null ? `${(sim.mu * 100).toFixed(2)}%` : "N/A"}</div>
              </div>
              <div>
                <span className="text-slate-500">연간 변동성 (σ)</span>
                <div className="font-medium">{sim.sigma != null ? `${(sim.sigma * 100).toFixed(2)}%` : "N/A"}</div>
              </div>
              <div>
                <span className="text-slate-500">시뮬레이션 횟수</span>
                <div className="font-medium">{sim.num_simulations?.toLocaleString() ?? "N/A"}</div>
              </div>
              <div>
                <span className="text-slate-500">분석 일수</span>
                <div className="font-medium">{sim.input_days_used ?? "N/A"}일</div>
              </div>
            </div>
          </div>
        </div>
        <div className="text-xs text-slate-400 pt-3 mt-3 border-t">기준일: {sim.as_of_date}</div>
      </div>

      {/* Fan Chart */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">확률 분포 팬차트</h3>
        <FanChart horizons={horizons} basePrice={sim.base_price ?? 0} />
      </div>

      {/* Horizon Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Object.entries(horizons).map(([key, h]) => (
          <HorizonCard key={key} horizon={h as SimulationHorizon} basePrice={sim.base_price ?? 0} />
        ))}
      </div>

      {/* Target Probabilities */}
      {sim.target_probs && Object.keys(sim.target_probs).length > 0 && (
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">
            <Target className="w-5 h-5 inline mr-2" />
            목표가 도달 확률
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 border-b">
                  <th className="text-left py-2">목표 배수</th>
                  {Object.values(horizons).map((h: any) => (
                    <th key={h.label} className="text-center py-2">{h.label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(sim.target_probs).map(([mult, probs]) => (
                  <tr key={mult} className="border-b border-slate-50">
                    <td className="py-2 font-medium">×{mult} ({formatKRW((sim.base_price ?? 0) * parseFloat(mult))}원)</td>
                    {Object.entries(probs as Record<string, number>).map(([hKey, prob]) => (
                      <td key={hKey} className="text-center py-2">
                        <span className={cn(
                          "font-medium",
                          prob >= 0.5 ? "text-emerald-600" : prob >= 0.2 ? "text-blue-600" : "text-slate-400"
                        )}>
                          {(prob * 100).toFixed(1)}%
                        </span>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Methodology */}
      <div className="bg-slate-50 rounded-lg border border-slate-200 p-6">
        <h3 className="text-sm font-semibold text-slate-800 mb-2">몬테카를로 시뮬레이션이란?</h3>
        <div className="text-sm text-slate-600 space-y-2">
          <p>
            과거 주가 데이터에서 추출한 수익률과 변동성을 기반으로 기하 브라운 운동(GBM) 모델을 사용하여
            10,000개의 미래 가격 경로를 시뮬레이션합니다.
          </p>
          <ul className="list-disc list-inside space-y-1 text-xs">
            <li><strong>팬차트:</strong> 5%, 25%, 50%, 75%, 95% 백분위 가격 범위</li>
            <li><strong>시뮬레이션 점수:</strong> 6개월 기대수익률(40%), 3개월 상승확률(35%), 3개월 VaR(25%) 종합</li>
          </ul>
          <p className="text-xs text-slate-500 pt-2 border-t">
            이 시뮬레이션은 과거 데이터를 기반으로 한 통계적 추정이며, 미래 수익을 보장하지 않습니다.
          </p>
        </div>
      </div>
    </div>
  );
}

function FanChart({ horizons, basePrice }: { horizons: Record<string, SimulationHorizon>; basePrice: number }) {
  const sortedEntries = Object.entries(horizons).sort(([a], [b]) => Number(a) - Number(b));

  if (sortedEntries.length === 0) {
    return <div className="h-64 flex items-center justify-center text-slate-400">데이터 없음</div>;
  }

  const labels = ["현재", ...sortedEntries.map(([, h]) => h.label)];
  const p5 = [basePrice, ...sortedEntries.map(([, h]) => h.p5 ?? basePrice)];
  const p25 = [basePrice, ...sortedEntries.map(([, h]) => h.p25 ?? basePrice)];
  const p50 = [basePrice, ...sortedEntries.map(([, h]) => h.p50 ?? basePrice)];
  const p75 = [basePrice, ...sortedEntries.map(([, h]) => h.p75 ?? basePrice)];
  const p95 = [basePrice, ...sortedEntries.map(([, h]) => h.p95 ?? basePrice)];

  const option = {
    tooltip: {
      trigger: "axis",
      formatter: (params: any[]) => {
        const idx = params[0]?.dataIndex;
        return `<strong>${labels[idx]}</strong><br/>
          95%: ${formatKRW(p95[idx])}원<br/>
          75%: ${formatKRW(p75[idx])}원<br/>
          중앙값: ${formatKRW(p50[idx])}원<br/>
          25%: ${formatKRW(p25[idx])}원<br/>
          5%: ${formatKRW(p5[idx])}원`;
      },
    },
    grid: { left: "10%", right: "4%", top: "8%", bottom: "10%" },
    xAxis: { type: "category", data: labels, axisLabel: { fontSize: 11 } },
    yAxis: {
      type: "value",
      axisLabel: { formatter: (v: number) => formatKRW(v) },
      scale: true,
      splitLine: { lineStyle: { color: "#f1f5f9" } },
    },
    series: [
      // Bottom stack (invisible, just for stacking offset)
      { name: "base", type: "line", data: p5, lineStyle: { opacity: 0 }, itemStyle: { opacity: 0 }, stack: "band", areaStyle: { opacity: 0 }, symbol: "none" },
      // 5-25 band (light)
      { name: "5%-25%", type: "line", data: p25.map((v, i) => v - p5[i]), lineStyle: { opacity: 0 }, itemStyle: { opacity: 0 }, stack: "band", areaStyle: { color: "rgba(59, 130, 246, 0.1)" }, symbol: "none" },
      // 25-75 band (medium)
      { name: "25%-75%", type: "line", data: p75.map((v, i) => v - p25[i]), lineStyle: { opacity: 0 }, itemStyle: { opacity: 0 }, stack: "band", areaStyle: { color: "rgba(59, 130, 246, 0.25)" }, symbol: "none" },
      // 75-95 band (light)
      { name: "75%-95%", type: "line", data: p95.map((v, i) => v - p75[i]), lineStyle: { opacity: 0 }, itemStyle: { opacity: 0 }, stack: "band", areaStyle: { color: "rgba(59, 130, 246, 0.1)" }, symbol: "none" },
      // Median line
      { name: "중앙값", type: "line", data: p50, lineStyle: { width: 2, color: "#3b82f6" }, itemStyle: { color: "#3b82f6" }, symbol: "circle", symbolSize: 6 },
      // Base price reference line
      { name: "현재가", type: "line", data: Array(labels.length).fill(basePrice), lineStyle: { width: 1, type: "dashed", color: "#94a3b8" }, itemStyle: { opacity: 0 }, symbol: "none" },
    ],
  };

  return <ReactECharts option={option} style={{ height: 350 }} />;
}

function HorizonCard({ horizon, basePrice: _basePrice }: { horizon: SimulationHorizon; basePrice: number }) {
  const returnPct = horizon.expected_return_pct;
  const isPositive = (returnPct ?? 0) > 0;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <h4 className="font-semibold text-slate-800 mb-3">{horizon.label}</h4>
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">기대수익률</span>
          <span className={cn("font-semibold", isPositive ? "text-emerald-600" : "text-red-600")}>
            {returnPct != null ? `${returnPct > 0 ? "+" : ""}${returnPct.toFixed(1)}%` : "N/A"}
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">VaR (5%)</span>
          <span className="font-medium text-red-600">
            {horizon.var_5pct_pct != null ? `${horizon.var_5pct_pct.toFixed(1)}%` : "N/A"}
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">상승 확률</span>
          <span className="font-medium text-blue-600">
            {horizon.upside_prob != null ? `${(horizon.upside_prob * 100).toFixed(1)}%` : "N/A"}
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">중앙값</span>
          <span className="font-medium">{horizon.p50 != null ? formatKRW(horizon.p50) + "원" : "N/A"}</span>
        </div>
        <div className="text-xs text-slate-400 pt-2 border-t">
          범위: {horizon.p5 != null ? formatKRW(horizon.p5) : "?"} ~ {horizon.p95 != null ? formatKRW(horizon.p95) : "?"}원
        </div>
      </div>
    </div>
  );
}
