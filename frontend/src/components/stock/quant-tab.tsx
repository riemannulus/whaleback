"use client";

import { useQuantValuation, useFScore } from "@/lib/queries";
import { GaugeChart } from "@/components/charts/gauge-chart";
import { cn, formatKRW, formatPercent } from "@/lib/utils";
import { CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import type { FScoreCriterion } from "@/types/api";

interface QuantTabProps {
  ticker: string;
}

const gradeColors: Record<string, string> = {
  "A+": "bg-emerald-100 text-emerald-800 border-emerald-300",
  A: "bg-green-100 text-green-800 border-green-300",
  "B+": "bg-sky-100 text-sky-800 border-sky-300",
  B: "bg-blue-100 text-blue-800 border-blue-300",
  "C+": "bg-yellow-100 text-yellow-800 border-yellow-300",
  C: "bg-orange-100 text-orange-800 border-orange-300",
  D: "bg-red-100 text-red-800 border-red-300",
  F: "bg-gray-100 text-gray-800 border-gray-300",
};

const gradeExplanations: Record<string, string> = {
  "A+": "최우량 - 저평가 + 펀더멘털 우수",
  A: "우량 - 저평가 또는 펀더멘털 우수",
  "B+": "양호 - 적정가 + 펀더멘털 무난",
  B: "보통 - 적정가 수준",
  "C+": "주의 - 고평가 또는 펀더멘털 약화",
  C: "경고 - 고평가 + 펀더멘털 약화",
  D: "위험 - 심각한 고평가 또는 재무 악화",
  F: "매우 위험 - 투자 부적합",
};

export function QuantTab({ ticker }: QuantTabProps) {
  const { data: valuation, isLoading: valuationLoading, error: valuationError } = useQuantValuation(ticker);
  const { data: fscore, isLoading: fscoreLoading, error: fscoreError } = useFScore(ticker);

  if (valuationLoading || fscoreLoading) {
    return (
      <div className="space-y-6">
        <div className="h-48 bg-slate-100 animate-pulse rounded-lg" />
        <div className="h-96 bg-slate-100 animate-pulse rounded-lg" />
        <div className="h-32 bg-slate-100 animate-pulse rounded-lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Valuation Card */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">정량 밸류에이션</h3>
        {valuationError || !valuation?.data ? (
          <div className="flex items-center gap-2 text-amber-600">
            <AlertCircle className="w-5 h-5" />
            <span>밸류에이션 데이터를 불러올 수 없습니다.</span>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <div className="text-sm text-slate-500">현재가</div>
                <div className="text-2xl font-bold text-slate-800">
                  {formatKRW(valuation.data.current_price)}원
                </div>
              </div>
              <div>
                <div className="text-sm text-slate-500">RIM 적정가</div>
                <div className="text-2xl font-bold text-blue-600">
                  {formatKRW(valuation.data.rim_value)}원
                </div>
              </div>
              <div>
                <div className="text-sm text-slate-500">안전마진</div>
                <div
                  className={cn(
                    "text-2xl font-bold",
                    (valuation.data.safety_margin_pct ?? 0) > 0 ? "text-green-600" : "text-red-600"
                  )}
                >
                  {formatPercent(valuation.data.safety_margin_pct)}
                </div>
              </div>
            </div>

            {/* Safety Margin Bar */}
            <div className="space-y-2">
              <div className="text-sm text-slate-600">안전마진 범위</div>
              <div className="relative h-8 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={cn(
                    "absolute top-0 left-0 h-full transition-all",
                    (valuation.data.safety_margin_pct ?? 0) > 0 ? "bg-green-500" : "bg-red-500"
                  )}
                  style={{
                    width: `${Math.min(Math.abs(valuation.data.safety_margin_pct ?? 0), 100)}%`,
                  }}
                />
                <div className="absolute inset-0 flex items-center justify-center text-sm font-medium text-slate-700">
                  {valuation.data.is_undervalued ? "저평가" : "고평가"}
                </div>
              </div>
            </div>

            {/* Grade Badge */}
            {valuation.data.grade && (
              <div className="flex items-center gap-3">
                <span className="text-sm text-slate-600">투자등급</span>
                <span
                  className={cn(
                    "px-3 py-1 rounded-md border font-semibold text-sm",
                    gradeColors[valuation.data.grade] || gradeColors.F
                  )}
                >
                  {valuation.data.grade}
                </span>
                <span className="text-sm text-slate-500">{valuation.data.grade_label}</span>
              </div>
            )}

            <div className="text-xs text-slate-400 pt-2 border-t">
              기준일: {valuation.data.as_of_date}
            </div>
          </div>
        )}
      </div>

      {/* F-Score Breakdown */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">F-Score 분석</h3>
        {fscoreError || !fscore?.data ? (
          <div className="flex items-center gap-2 text-amber-600">
            <AlertCircle className="w-5 h-5" />
            <span>F-Score 데이터를 불러올 수 없습니다.</span>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Total Score with Gauge */}
            <div className="flex flex-col items-center">
              <GaugeChart
                value={fscore.data.total_score}
                max={fscore.data.max_score}
                label={`${fscore.data.total_score} / ${fscore.data.max_score}`}
                color={fscore.data.total_score >= 7 ? "#10b981" : fscore.data.total_score >= 4 ? "#0ea5e9" : "#ef4444"}
                height={180}
              />
              <div className="text-sm text-slate-500 mt-2">
                {fscore.data.total_score >= 7
                  ? "우수 (Strong)"
                  : fscore.data.total_score >= 4
                  ? "양호 (Moderate)"
                  : "취약 (Weak)"}
              </div>
            </div>

            {/* Criteria Checklist */}
            <div className="space-y-2">
              <div className="text-sm font-medium text-slate-700 mb-3">상세 평가 항목</div>
              {fscore.data.criteria.map((criterion: FScoreCriterion, idx: number) => (
                <div
                  key={idx}
                  className={cn(
                    "flex items-start gap-3 p-3 rounded-lg",
                    criterion.score > 0 ? "bg-green-50" : "bg-slate-50"
                  )}
                >
                  {criterion.score > 0 ? (
                    <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                  ) : (
                    <XCircle className="w-5 h-5 text-slate-400 flex-shrink-0 mt-0.5" />
                  )}
                  <div className="flex-1">
                    <div className="text-sm font-medium text-slate-800">{criterion.label}</div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {criterion.name}: {criterion.value != null ? criterion.value.toFixed(2) : "N/A"}
                      {criterion.note && ` (${criterion.note})`}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Data Completeness */}
            <div className="space-y-2">
              <div className="text-sm text-slate-600">데이터 완전성</div>
              <div className="relative h-4 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={cn(
                    "absolute top-0 left-0 h-full transition-all",
                    fscore.data.data_completeness >= 0.8
                      ? "bg-green-500"
                      : fscore.data.data_completeness >= 0.5
                      ? "bg-yellow-500"
                      : "bg-red-500"
                  )}
                  style={{ width: `${fscore.data.data_completeness * 100}%` }}
                />
              </div>
              <div className="text-xs text-slate-500">
                {(fscore.data.data_completeness * 100).toFixed(0)}% 데이터 확보
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Investment Grade Explanation */}
      <div className="bg-slate-50 rounded-lg border border-slate-200 p-6">
        <h3 className="text-sm font-semibold text-slate-800 mb-3">투자등급 가이드</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          {Object.entries(gradeExplanations).map(([grade, explanation]) => (
            <div key={grade} className="flex items-center gap-2">
              <span
                className={cn(
                  "px-2 py-0.5 rounded border font-semibold text-xs",
                  gradeColors[grade] || gradeColors.F
                )}
              >
                {grade}
              </span>
              <span className="text-slate-600">{explanation}</span>
            </div>
          ))}
        </div>
        <div className="mt-4 text-xs text-slate-500 border-t pt-3">
          <strong>방법론:</strong> RIM(잔여이익모형) 기반 적정가 산출 + Piotroski F-Score 펀더멘털 평가를 결합한 정량적
          투자등급입니다. 안전마진이 클수록, F-Score가 높을수록 우수한 등급을 부여합니다.
        </div>
      </div>
    </div>
  );
}
