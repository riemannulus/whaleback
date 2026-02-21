"use client";

import { useCompositeDetail } from "@/lib/queries";
import { GaugeChart } from "@/components/charts/gauge-chart";
import { cn } from "@/lib/utils";
import { AlertCircle, TrendingUp, Shield, Activity, BarChart3, Telescope } from "lucide-react";
import ReactECharts from "echarts-for-react";
import type { CompositeDetail, FlowAnalysis, TechnicalAnalysis, RiskAnalysis } from "@/types/api";

interface CompositeTabProps {
  ticker: string;
}

const tierColors: Record<string, string> = {
  excellent: "bg-emerald-100 text-emerald-800 border-emerald-300",
  good: "bg-green-100 text-green-800 border-green-300",
  fair: "bg-blue-100 text-blue-800 border-blue-300",
  average: "bg-yellow-100 text-yellow-800 border-yellow-300",
  caution: "bg-orange-100 text-orange-800 border-orange-300",
  risk: "bg-red-100 text-red-800 border-red-300",
  unknown: "bg-gray-100 text-gray-800 border-gray-300",
};

const scoreBarColor = (score: number | null): string => {
  if (score === null) return "bg-gray-200";
  if (score >= 75) return "bg-emerald-500";
  if (score >= 60) return "bg-green-500";
  if (score >= 40) return "bg-blue-500";
  if (score >= 25) return "bg-yellow-500";
  return "bg-red-500";
};

const signalLabel: Record<string, { text: string; color: string }> = {
  extreme_buying: { text: "역발상 매도 경고", color: "text-red-600" },
  extreme_selling: { text: "역발상 매수 기회", color: "text-green-600" },
  neutral: { text: "중립", color: "text-slate-600" },
  smart_accumulation: { text: "스마트머니 매집", color: "text-green-600" },
  smart_distribution: { text: "스마트머니 매도", color: "text-red-600" },
  mixed: { text: "혼재", color: "text-slate-600" },
};

export function CompositeTab({ ticker }: CompositeTabProps) {
  const { data, isLoading, error } = useCompositeDetail(ticker);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-48 bg-slate-100 animate-pulse rounded-lg" />
        <div className="h-32 bg-slate-100 animate-pulse rounded-lg" />
        <div className="h-64 bg-slate-100 animate-pulse rounded-lg" />
      </div>
    );
  }

  if (error || !data?.data) {
    return (
      <div className="flex items-center gap-2 text-amber-600 p-6">
        <AlertCircle className="w-5 h-5" />
        <span>종합 분석 데이터를 불러올 수 없습니다.</span>
      </div>
    );
  }

  const detail: CompositeDetail = data.data;
  const { composite } = detail;

  return (
    <div className="space-y-6">
      {/* WCS Score Card */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">Whaleback 종합 점수 (WCS)</h3>
        <div className="flex flex-col md:flex-row items-center gap-8">
          {/* Gauge */}
          <div className="flex flex-col items-center">
            <GaugeChart
              value={composite.composite_score ?? 0}
              max={100}
              label={composite.composite_score != null ? `${composite.composite_score.toFixed(1)}` : "N/A"}
              color={
                composite.score_color === "emerald" ? "#10b981" :
                composite.score_color === "green" ? "#22c55e" :
                composite.score_color === "blue" ? "#3b82f6" :
                composite.score_color === "yellow" ? "#eab308" :
                composite.score_color === "orange" ? "#f97316" :
                composite.score_color === "red" ? "#ef4444" : "#94a3b8"
              }
              height={200}
            />
          </div>

          {/* Score Info */}
          <div className="flex-1 space-y-3">
            <div className="flex items-center gap-3">
              <span
                className={cn(
                  "px-3 py-1 rounded-md border font-semibold text-sm",
                  tierColors[composite.score_tier || "unknown"]
                )}
              >
                {composite.score_label || "분석 불가"}
              </span>
              <span className="text-sm text-slate-500">
                신뢰도: {composite.confidence != null ? `${(composite.confidence * 100).toFixed(0)}%` : "N/A"}
                ({composite.axes_available || 0}/4 축)
              </span>
            </div>

            {/* Action Label */}
            {composite.action_label && (
              <div className="p-3 bg-slate-50 rounded-lg">
                <div className="font-medium text-slate-800">{composite.action_label}</div>
                <div className="text-sm text-slate-600 mt-1">{composite.action_description}</div>
              </div>
            )}

            {/* Confluence */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-600">시그널 합류:</span>
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div
                    key={i}
                    className={cn(
                      "w-3 h-3 rounded-full",
                      i <= (composite.confluence_tier || 0) ? "bg-blue-500" : "bg-slate-200"
                    )}
                  />
                ))}
              </div>
              <span className="text-sm text-slate-500">Tier {composite.confluence_tier || "-"}</span>
            </div>

            {/* Divergence Warning */}
            {composite.divergence_label && (
              <div className="flex items-center gap-2 text-amber-600 text-sm">
                <AlertCircle className="w-4 h-4" />
                <span>{composite.divergence_label}</span>
              </div>
            )}
          </div>
        </div>

        <div className="text-xs text-slate-400 pt-3 mt-3 border-t">
          기준일: {composite.trade_date}
        </div>
      </div>

      {/* Axis Breakdown */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">축별 점수</h3>
        <div className="space-y-4">
          {[
            { label: "가치 (Value)", score: composite.value_score, icon: TrendingUp },
            { label: "수급 (Flow)", score: composite.flow_score, icon: BarChart3 },
            { label: "모멘텀 (Momentum)", score: composite.momentum_score, icon: Activity },
            { label: "전망 (Forecast)", score: composite.forecast_score, icon: Telescope },
          ].map(({ label, score, icon: Icon }) => (
            <div key={label} className="space-y-1">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                  <Icon className="w-4 h-4" />
                  {label}
                </div>
                <span className="text-sm font-semibold text-slate-800">
                  {score != null ? score.toFixed(1) : "N/A"}
                </span>
              </div>
              <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={cn("h-full rounded-full transition-all", scoreBarColor(score))}
                  style={{ width: score != null ? `${Math.min(score, 100)}%` : "0%" }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Radar Chart */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">4축 레이더</h3>
        <RadarChart
          value={composite.value_score}
          flow={composite.flow_score}
          momentum={composite.momentum_score}
          forecast={composite.forecast_score}
        />
      </div>

      {/* Flow Analysis */}
      {detail.flow && <FlowCard flow={detail.flow} />}

      {/* Technical Indicators */}
      {detail.technical && <TechnicalCard technical={detail.technical} />}

      {/* Risk Metrics */}
      {detail.risk && <RiskCard risk={detail.risk} />}

      {/* Methodology */}
      <div className="bg-slate-50 rounded-lg border border-slate-200 p-6">
        <h3 className="text-sm font-semibold text-slate-800 mb-3">WCS 방법론</h3>
        <div className="text-xs text-slate-600 space-y-2">
          <p><strong>가치(30%):</strong> F-Score(비선형 정규화) + RIM 안전마진(시그모이드) 결합</p>
          <p><strong>수급(30%):</strong> 기관/외국인/연기금/사모펀드/기타법인 순매수 종합 Whale Score + 섹터 수급 보너스</p>
          <p><strong>모멘텀(20%):</strong> KOSPI 대비 상대강도 + 섹터 회전 보정</p>
          <p><strong>전망(20%):</strong> 몬테카를로 시뮬레이션 점수 (6개월 기대수익률 + 상승확률 + VaR)</p>
          <p className="pt-2 border-t border-slate-300"><strong>합류(Confluence):</strong> 네 축의 신호 일치도에 따라 1-5 티어 부여. 티어가 높을수록 신호 신뢰도가 높습니다.</p>
        </div>
      </div>
    </div>
  );
}

// --- Sub-components ---

function FlowCard({ flow }: { flow: FlowAnalysis }) {
  const retailSignal = signalLabel[flow.retail_signal || "neutral"] || signalLabel.neutral;
  const divSignal = signalLabel[flow.divergence_signal || "mixed"] || signalLabel.mixed;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-6">
      <h3 className="text-lg font-semibold text-slate-800 mb-4">수급 흐름 분석</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Retail Contrarian */}
        <div className="space-y-2">
          <div className="text-sm text-slate-500">개인 역발상 신호</div>
          <div className={cn("text-lg font-semibold", retailSignal.color)}>
            {retailSignal.text}
          </div>
          <div className="text-xs text-slate-400">
            Z-Score: {flow.retail_z?.toFixed(2) ?? "N/A"}
          </div>
        </div>
        {/* Smart/Dumb Divergence */}
        <div className="space-y-2">
          <div className="text-sm text-slate-500">스마트/개인 괴리</div>
          <div className={cn("text-lg font-semibold", divSignal.color)}>
            {divSignal.text}
          </div>
          <div className="text-xs text-slate-400">
            괴리도: {flow.divergence_score?.toFixed(4) ?? "N/A"}
          </div>
        </div>
        {/* Momentum Shift */}
        <div className="space-y-2">
          <div className="text-sm text-slate-500">수급 전환</div>
          <div className="text-lg font-semibold text-slate-800">
            {shiftLabel(flow.shift_signal)}
          </div>
          <div className="text-xs text-slate-400">
            전환 강도: {flow.shift_score?.toFixed(1) ?? "N/A"}
          </div>
        </div>
      </div>
    </div>
  );
}

function TechnicalCard({ technical }: { technical: TechnicalAnalysis }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-6">
      <h3 className="text-lg font-semibold text-slate-800 mb-4">기술적 지표</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Disparity */}
        <div className="space-y-2">
          <div className="text-sm font-medium text-slate-700">이격도</div>
          <div className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">20일</span>
              <span className="font-medium">{technical.disparity_20d?.toFixed(1) ?? "-"}%</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">60일</span>
              <span className="font-medium">{technical.disparity_60d?.toFixed(1) ?? "-"}%</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">120일</span>
              <span className="font-medium">{technical.disparity_120d?.toFixed(1) ?? "-"}%</span>
            </div>
          </div>
          <div className="text-xs text-slate-400">{disparityLabel(technical.disparity_signal)}</div>
        </div>
        {/* Bollinger */}
        <div className="space-y-2">
          <div className="text-sm font-medium text-slate-700">볼린저 밴드</div>
          <div className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">%B</span>
              <span className="font-medium">{technical.bb_percent_b?.toFixed(2) ?? "-"}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">밴드폭</span>
              <span className="font-medium">{technical.bb_bandwidth?.toFixed(1) ?? "-"}%</span>
            </div>
          </div>
          <div className="text-xs text-slate-400">{bbLabel(technical.bb_signal)}</div>
        </div>
        {/* MACD */}
        <div className="space-y-2">
          <div className="text-sm font-medium text-slate-700">MACD</div>
          <div className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">MACD</span>
              <span className="font-medium">{technical.macd_value?.toFixed(0) ?? "-"}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">히스토그램</span>
              <span className={cn("font-medium", (technical.macd_histogram ?? 0) > 0 ? "text-red-600" : "text-blue-600")}>
                {technical.macd_histogram?.toFixed(0) ?? "-"}
              </span>
            </div>
          </div>
          <div className="text-xs text-slate-400">{macdLabel(technical.macd_crossover)}</div>
        </div>
      </div>
    </div>
  );
}

function RiskCard({ risk }: { risk: RiskAnalysis }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-6">
      <h3 className="text-lg font-semibold text-slate-800 mb-4">리스크 지표</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Volatility */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
            <Activity className="w-4 h-4" />
            변동성
          </div>
          <div className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">20일</span>
              <span className="font-medium">{risk.volatility_20d?.toFixed(1) ?? "-"}%</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">60일</span>
              <span className="font-medium">{risk.volatility_60d?.toFixed(1) ?? "-"}%</span>
            </div>
          </div>
          <div className={cn("text-xs font-medium", riskColor(risk.risk_level))}>
            {riskLabel(risk.risk_level)}
          </div>
        </div>
        {/* Beta */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
            <TrendingUp className="w-4 h-4" />
            베타 (시장 민감도)
          </div>
          <div className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">60일</span>
              <span className="font-medium">{risk.beta_60d?.toFixed(2) ?? "-"}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">1년</span>
              <span className="font-medium">{risk.beta_252d?.toFixed(2) ?? "-"}</span>
            </div>
          </div>
          <div className="text-xs text-slate-400">{betaLabel(risk.beta_interpretation)}</div>
        </div>
        {/* Drawdown */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
            <Shield className="w-4 h-4" />
            최대 낙폭 (MDD)
          </div>
          <div className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">60일</span>
              <span className="font-medium text-red-600">{risk.mdd_60d != null ? `${(risk.mdd_60d * 100).toFixed(1)}%` : "-"}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">현재</span>
              <span className="font-medium text-red-600">{risk.current_drawdown != null ? `${(risk.current_drawdown * 100).toFixed(1)}%` : "-"}</span>
            </div>
          </div>
          <div className="text-xs text-slate-400">{risk.recovery_label || "-"}</div>
        </div>
      </div>
    </div>
  );
}

// --- Sub-components (charts) ---

function RadarChart({ value, flow, momentum, forecast }: { value: number | null; flow: number | null; momentum: number | null; forecast: number | null }) {
  const option = {
    radar: {
      indicator: [
        { name: "가치", max: 100 },
        { name: "수급", max: 100 },
        { name: "모멘텀", max: 100 },
        { name: "전망", max: 100 },
      ],
      shape: "polygon",
      splitNumber: 4,
      axisName: { color: "#475569", fontSize: 12 },
      splitArea: { areaStyle: { color: ["rgba(241, 245, 249, 0.3)", "rgba(241, 245, 249, 0.5)"] } },
      splitLine: { lineStyle: { color: "#e2e8f0" } },
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: [value ?? 0, flow ?? 0, momentum ?? 0, forecast ?? 0],
            name: "WCS",
            areaStyle: { color: "rgba(59, 130, 246, 0.2)" },
            lineStyle: { color: "#3b82f6", width: 2 },
            itemStyle: { color: "#3b82f6" },
          },
        ],
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: 280 }} />;
}

// --- Label helpers ---

function shiftLabel(signal: string | null): string {
  const labels: Record<string, string> = {
    strong_bullish_shift: "강한 상승 전환",
    strong_bearish_shift: "강한 하락 전환",
    strong_shift: "강한 수급 전환",
    mild_bullish_shift: "완만한 상승 전환",
    mild_bearish_shift: "완만한 하락 전환",
    mild_shift: "완만한 수급 전환",
    no_shift: "전환 없음",
  };
  return labels[signal || ""] || "전환 없음";
}

function disparityLabel(signal: string | null): string {
  const labels: Record<string, string> = {
    strong_oversold: "강한 과매도",
    oversold: "과매도",
    strong_overbought: "강한 과매수",
    overbought: "과매수",
    neutral: "중립",
  };
  return labels[signal || ""] || "중립";
}

function bbLabel(signal: string | null): string {
  const labels: Record<string, string> = {
    upper_break: "상단 돌파",
    lower_support: "하단 지지",
    squeeze: "밴드 수축",
    neutral: "중립",
  };
  return labels[signal || ""] || "중립";
}

function macdLabel(crossover: string | null): string {
  const labels: Record<string, string> = {
    golden_cross: "골든크로스",
    dead_cross: "데드크로스",
    none: "없음",
  };
  return labels[crossover || ""] || "없음";
}

function riskLabel(level: string | null): string {
  const labels: Record<string, string> = {
    low: "저변동",
    medium: "보통",
    high: "고변동",
    very_high: "초고변동",
  };
  return labels[level || ""] || "알 수 없음";
}

function riskColor(level: string | null): string {
  const colors: Record<string, string> = {
    low: "text-green-600",
    medium: "text-blue-600",
    high: "text-orange-600",
    very_high: "text-red-600",
  };
  return colors[level || ""] || "text-slate-400";
}

function betaLabel(interpretation: string | null): string {
  const labels: Record<string, string> = {
    defensive: "방어적 (시장 변동 대비 안정)",
    neutral: "중립 (시장 추종)",
    aggressive: "공격적 (시장 변동 증폭)",
    highly_aggressive: "초공격적 (고위험)",
  };
  return labels[interpretation || ""] || "알 수 없음";
}
