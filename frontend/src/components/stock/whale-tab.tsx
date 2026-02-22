"use client";

import { useWhaleScore, useInvestorHistory } from "@/lib/queries";
import { GaugeChart } from "@/components/charts/gauge-chart";
import { BarChart } from "@/components/charts/bar-chart";
import { cn, formatLargeNumber } from "@/lib/utils";
import { AlertCircle, TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { InvestorData } from "@/types/api";

interface WhaleTabProps {
  ticker: string;
}

const signalColors: Record<string, { bg: string; text: string; border: string; icon: JSX.Element }> = {
  strong_accumulation: {
    bg: "bg-emerald-100",
    text: "text-emerald-800",
    border: "border-emerald-300",
    icon: <TrendingUp className="w-4 h-4" />,
  },
  mild_accumulation: {
    bg: "bg-blue-100",
    text: "text-blue-800",
    border: "border-blue-300",
    icon: <TrendingUp className="w-4 h-4" />,
  },
  neutral: {
    bg: "bg-gray-100",
    text: "text-gray-800",
    border: "border-gray-300",
    icon: <Minus className="w-4 h-4" />,
  },
  distribution: {
    bg: "bg-red-100",
    text: "text-red-800",
    border: "border-red-300",
    icon: <TrendingDown className="w-4 h-4" />,
  },
};

const componentLabels: Record<string, string> = {
  institution_net: "기관",
  foreign_net: "외국인",
  pension_net: "연기금",
  private_equity_net: "사모펀드",
  other_corp_net: "기타법인",
};

export function WhaleTab({ ticker }: WhaleTabProps) {
  const { data: whaleScore, isLoading: scoreLoading, error: scoreError } = useWhaleScore(ticker);
  const { data: investorHistory, isLoading: historyLoading, error: historyError } = useInvestorHistory(ticker);

  // Get last 60 days of investor data
  const last60Days = investorHistory?.data?.slice(-60) || [];

  if (scoreLoading || historyLoading) {
    return (
      <div className="space-y-6">
        <div className="h-64 bg-slate-100 animate-pulse rounded-lg" />
        <div className="h-96 bg-slate-100 animate-pulse rounded-lg" />
        <div className="h-96 bg-slate-100 animate-pulse rounded-lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Whale Score Card */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">고래 스코어</h3>
        {scoreError || !whaleScore?.data ? (
          <div className="flex items-center gap-2 text-amber-600">
            <AlertCircle className="w-5 h-5" />
            <span>고래 스코어 데이터를 불러올 수 없습니다.</span>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Score Gauge */}
            <div className="flex flex-col items-center">
              <GaugeChart
                value={whaleScore.data.whale_score}
                max={100}
                label={`${whaleScore.data.whale_score.toFixed(0)}`}
                color={
                  whaleScore.data.whale_score >= 70
                    ? "#10b981"
                    : whaleScore.data.whale_score >= 40
                    ? "#0ea5e9"
                    : "#ef4444"
                }
                height={200}
              />
              <div className="mt-4 flex items-center gap-2">
                <span
                  className={cn(
                    "px-3 py-1 rounded-md border font-semibold text-sm flex items-center gap-1.5",
                    signalColors[whaleScore.data.signal]?.bg,
                    signalColors[whaleScore.data.signal]?.text,
                    signalColors[whaleScore.data.signal]?.border
                  )}
                >
                  {signalColors[whaleScore.data.signal]?.icon}
                  {whaleScore.data.signal_label}
                </span>
              </div>
            </div>

            <div className="text-xs text-slate-400 text-center border-t pt-3">
              기준일: {whaleScore.data.as_of_date} | 조회기간: {whaleScore.data.lookback_days}일
            </div>
          </div>
        )}
      </div>

      {/* Component Breakdown */}
      {whaleScore?.data?.components && (
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">세력별 누적 매수 강도</h3>
          <div className="space-y-4">
            {Object.entries(whaleScore.data.components).map(([key, value]) => {
              const label = componentLabels[key] || key;
              const netTotal = (value as { net_total: number; consistency: number }).net_total;
              const consistency = (value as { net_total: number; consistency: number }).consistency;
              const maxAbsValue = Math.max(
                ...Object.values(whaleScore.data.components || {}).map((v) => Math.abs((v as { net_total: number; consistency: number }).net_total))
              );
              const barWidth = maxAbsValue > 0 ? (Math.abs(netTotal) / maxAbsValue) * 100 : 0;

              return (
                <div key={key} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium text-slate-700">{label}</span>
                    <span
                      className={cn("font-semibold", netTotal > 0 ? "text-green-600" : netTotal < 0 ? "text-red-600" : "text-slate-400")}
                    >
                      {formatLargeNumber(netTotal)}
                    </span>
                  </div>
                  <div className="relative h-6 bg-slate-100 rounded-md overflow-hidden">
                    <div
                      className={cn(
                        "absolute top-0 h-full transition-all",
                        netTotal > 0 ? "bg-green-500 left-0 rounded-r-md" : netTotal < 0 ? "bg-red-500 right-0 rounded-l-md" : ""
                      )}
                      style={{ width: `${barWidth}%` }}
                    />
                    <div className="absolute inset-0 flex items-center justify-end px-2">
                      <span className="text-xs text-slate-600">
                        일관성: {(consistency * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Accumulation Timeline */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">일별 순매수 추이 (최근 60일)</h3>
        {historyError || last60Days.length === 0 ? (
          <div className="flex items-center gap-2 text-amber-600">
            <AlertCircle className="w-5 h-5" />
            <span>투자자별 거래 데이터를 불러올 수 없습니다.</span>
          </div>
        ) : (
          <div>
            <BarChart
              labels={last60Days.map((d: InvestorData) => d.trade_date.slice(5))}
              series={[
                {
                  name: "기관",
                  data: last60Days.map((d: InvestorData) => d.institution_net ?? 0),
                  color: "#3b82f6",
                },
                {
                  name: "외국인",
                  data: last60Days.map((d: InvestorData) => d.foreign_net ?? 0),
                  color: "#10b981",
                },
                {
                  name: "연기금",
                  data: last60Days.map((d: InvestorData) => d.pension_net ?? 0),
                  color: "#8b5cf6",
                },
                {
                  name: "사모펀드",
                  data: last60Days.map((d: InvestorData) => d.private_equity_net ?? 0),
                  color: "#f59e0b",
                },
                {
                  name: "기타법인",
                  data: last60Days.map((d: InvestorData) => d.other_corp_net ?? 0),
                  color: "#ef4444",
                },
              ]}
              height={350}
              stacked={false}
            />
            <div className="mt-4 text-xs text-slate-500">
              <strong>해석:</strong> 양(+)의 값은 순매수, 음(-)의 값은 순매도를 나타냅니다. 기관, 외국인, 연기금, 사모펀드, 기타법인의
              지속적인 순매수는 긍정적 신호로 해석됩니다.
            </div>
          </div>
        )}
      </div>

      {/* Methodology Note */}
      <div className="bg-slate-50 rounded-lg border border-slate-200 p-6">
        <h3 className="text-sm font-semibold text-slate-800 mb-2">고래 스코어란?</h3>
        <div className="text-sm text-slate-600 space-y-2">
          <p>
            기관, 외국인, 연기금, 사모펀드, 기타법인 등 5대 고래 투자자들의 매수/매도 패턴을 분석하여 0~100점 척도로 수치화한 지표입니다.
          </p>
          <ul className="list-disc list-inside space-y-1 text-xs">
            <li>
              <strong>70점 이상:</strong> 강력한 매집 (Strong Accumulation) - 고래들의 적극적 매수
            </li>
            <li>
              <strong>40~70점:</strong> 온건한 매집 (Mild Accumulation) - 점진적 매수
            </li>
            <li>
              <strong>30~40점:</strong> 중립 (Neutral) - 뚜렷한 방향성 없음
            </li>
            <li>
              <strong>30점 미만:</strong> 분산 (Distribution) - 고래들의 매도
            </li>
          </ul>
          <p className="text-xs text-slate-500 pt-2 border-t">
            <strong>방법론:</strong> 5대 투자 주체(기관, 외국인, 연기금, 사모펀드, 기타법인)의 누적 순매수량, 거래 일관성, 최근 모멘텀을 종합 평가하여 산출합니다. 단기 변동성에
            강건하도록 설계되었습니다.
          </p>
        </div>
      </div>
    </div>
  );
}
