"use client";

import { useSimulationResult } from "@/lib/queries";
import { GaugeChart } from "@/components/charts/gauge-chart";
import { cn, formatKRW } from "@/lib/utils";
import { AlertCircle, Target, Layers } from "lucide-react";
import ReactECharts from "echarts-for-react";
import type { SimulationResult, SimulationHorizon, SimulationModelBreakdown } from "@/types/api";

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
  const modelCount = sim.model_breakdown?.model_scores?.length ?? 1;

  return (
    <div className="space-y-6">
      {/* Simulation Score Card */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <h3 className="text-lg font-semibold text-slate-800">몬테카를로 시뮬레이션</h3>
          {modelCount > 1 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-indigo-50 border border-indigo-200 text-xs font-medium text-indigo-700">
              <Layers className="w-3 h-3" />
              {modelCount}모델 앙상블
            </span>
          )}
        </div>
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
            {modelCount > 1 && (
              <div className="text-xs text-slate-400 mt-1">앙상블 종합 점수</div>
            )}
          </div>
          <div className="flex-1 space-y-3">
            <div className="flex items-center gap-3 flex-wrap">
              <span className={cn("px-3 py-1 rounded-md border font-semibold text-sm", grade.bg, grade.text, grade.border)}>
                {gradeLabels[sim.simulation_grade || ""] || "분석 불가"}
              </span>
              <span className="text-sm text-slate-500">
                기준가: {sim.base_price != null ? formatKRW(sim.base_price) + "원" : "N/A"}
              </span>
              {(data.data as any)?.sentiment_applied && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
                  AI 뉴스 감성 반영됨
                </span>
              )}
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
                <span className="text-slate-500">시뮬레이션 경로</span>
                <div className="font-medium">
                  {sim.num_simulations?.toLocaleString() ?? "N/A"}
                  {modelCount > 1 && <span className="text-slate-400 font-normal"> × {modelCount}모델</span>}
                </div>
              </div>
              <div>
                <span className="text-slate-500">분석 기간</span>
                <div className="font-medium">{sim.input_days_used ?? "N/A"}거래일</div>
              </div>
            </div>
          </div>
        </div>
        <div className="text-xs text-slate-400 pt-3 mt-3 border-t">기준일: {sim.as_of_date}</div>
      </div>

      {/* Model Breakdown */}
      {sim.model_breakdown?.model_scores && sim.model_breakdown.model_scores.length > 1 && (
        <ModelBreakdownCard breakdown={sim.model_breakdown} />
      )}

      {/* Fan Chart */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <div className="flex items-baseline gap-2 mb-4">
          <h3 className="text-lg font-semibold text-slate-800">확률 분포 팬차트</h3>
          {modelCount > 1 && (
            <span className="text-xs text-slate-400">{modelCount}개 모델 앙상블 분포 기반</span>
          )}
        </div>
        <FanChart horizons={horizons} basePrice={sim.base_price ?? 0} />
      </div>

      {/* Horizon Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Object.entries(horizons)
          .sort(([a], [b]) => Number(a) - Number(b))
          .map(([key, h]) => (
          <HorizonCard key={key} horizon={h as SimulationHorizon} basePrice={sim.base_price ?? 0} />
        ))}
      </div>

      {/* Target Probabilities */}
      {sim.target_probs && Object.keys(sim.target_probs).length > 0 && (
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <div className="flex items-baseline gap-2 mb-4">
            <h3 className="text-lg font-semibold text-slate-800">
              <Target className="w-5 h-5 inline mr-2" />
              목표가 도달 확률
            </h3>
            {modelCount > 1 && (
              <span className="text-xs text-slate-400">앙상블 시뮬레이션 기준</span>
            )}
          </div>
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
            과거 주가 데이터에서 추출한 수익률과 변동성을 기반으로 4개의 확률 모델(GBM, GARCH, Heston, Merton)을
            앙상블하여 10,000개의 미래 가격 경로를 시뮬레이션합니다.
          </p>
          <ul className="list-disc list-inside space-y-1 text-xs">
            <li><strong>GBM:</strong> 기하 브라운 운동 (상수 변동성 기준 모델)</li>
            <li><strong>GARCH(1,1):</strong> 시간에 따라 변하는 변동성 군집 반영</li>
            <li><strong>Heston SV:</strong> 확률적 변동성 + 레버리지 효과 반영</li>
            <li><strong>Merton JD:</strong> 포아송 점프 프로세스로 급등/급락 반영</li>
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

const modelLabels: Record<string, string> = {
  gbm: "GBM",
  garch: "GARCH(1,1)",
  heston: "Heston SV",
  merton: "Merton JD",
};

const modelDescriptions: Record<string, string> = {
  gbm: "상수 변동성",
  garch: "시간가변 변동성",
  heston: "확률적 변동성",
  merton: "점프 확산",
};

function ModelBreakdownCard({ breakdown }: { breakdown: SimulationModelBreakdown }) {
  const scores = breakdown.model_scores;
  if (!scores || scores.length === 0) return null;

  // Find min/max for relative bar sizing
  const validScores = scores.map(s => s.score).filter((s): s is number => s != null);
  const maxScore = Math.max(...validScores, 1);

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-6">
      <div className="flex items-center gap-3 mb-4">
        <h3 className="text-lg font-semibold text-slate-800">모델별 점수 분석</h3>
        <span className="text-xs text-slate-400">각 모델의 독립 시뮬레이션 결과</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {scores.map((ms) => {
          const scoreColor =
            (ms.score ?? 0) >= 70 ? "text-emerald-600" :
            (ms.score ?? 0) >= 50 ? "text-blue-600" :
            (ms.score ?? 0) >= 30 ? "text-yellow-600" : "text-red-600";
          const barColor =
            (ms.score ?? 0) >= 70 ? "bg-emerald-400" :
            (ms.score ?? 0) >= 50 ? "bg-blue-400" :
            (ms.score ?? 0) >= 30 ? "bg-yellow-400" : "bg-red-400";
          const barWidth = ms.score != null ? Math.max(4, (ms.score / maxScore) * 100) : 0;

          return (
            <div key={ms.model} className="bg-slate-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-1">
                <div className="text-sm font-semibold text-slate-700">
                  {modelLabels[ms.model] || ms.model}
                </div>
                <div className={cn("text-lg font-bold", scoreColor)}>
                  {ms.score != null ? ms.score.toFixed(1) : "N/A"}
                </div>
              </div>
              <div className="text-xs text-slate-400 mb-2">
                {modelDescriptions[ms.model] || ""}
              </div>
              {/* Score bar */}
              <div className="h-1.5 bg-slate-200 rounded-full mb-2">
                <div className={cn("h-full rounded-full transition-all", barColor)} style={{ width: `${barWidth}%` }} />
              </div>
              {/* Weight indicator */}
              <div className="flex items-center gap-1.5 text-xs text-slate-500">
                <span>가중치</span>
                <div className="flex-1 h-1 bg-slate-200 rounded-full">
                  <div className="h-full bg-indigo-300 rounded-full" style={{ width: `${ms.weight * 100}%` }} />
                </div>
                <span className="font-medium">{(ms.weight * 100).toFixed(0)}%</span>
              </div>
            </div>
          );
        })}
      </div>
      <div className="text-xs text-slate-400 mt-3 pt-3 border-t flex items-center gap-4">
        <span>앙상블: {breakdown.ensemble_method === "weighted_pooling" ? "가중 풀링 (모델별 가중치 비례 샘플링)" : breakdown.ensemble_method || "N/A"}</span>
      </div>
    </div>
  );
}
