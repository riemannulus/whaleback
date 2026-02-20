"use client";

import { useStockDetail } from "@/lib/queries";
import { cn, formatKRW, formatPercent } from "@/lib/utils";
import { AlertCircle } from "lucide-react";

interface FundamentalsTabProps {
  ticker: string;
}

const fundamentalFields = [
  { key: "bps", label: "주당순자산 (BPS)", unit: "원", format: formatKRW },
  { key: "per", label: "주가수익비율 (PER)", unit: "배", format: (v: number | null) => (v != null ? v.toFixed(2) : "-") },
  { key: "pbr", label: "주가순자산비율 (PBR)", unit: "배", format: (v: number | null) => (v != null ? v.toFixed(2) : "-") },
  { key: "eps", label: "주당순이익 (EPS)", unit: "원", format: formatKRW },
  { key: "div", label: "배당수익률 (DIV)", unit: "%", format: (v: number | null) => (v != null ? v.toFixed(2) : "-") },
  { key: "dps", label: "주당배당금 (DPS)", unit: "원", format: formatKRW },
  { key: "roe", label: "자기자본이익률 (ROE)", unit: "%", format: (v: number | null) => (v != null ? v.toFixed(2) : "-") },
] as const;

export function FundamentalsTab({ ticker }: FundamentalsTabProps) {
  const { data: stockDetail, isLoading, error } = useStockDetail(ticker);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-64 bg-slate-100 animate-pulse rounded-lg" />
        <div className="h-48 bg-slate-100 animate-pulse rounded-lg" />
      </div>
    );
  }

  const fundamental = stockDetail?.data?.latest_fundamental;

  return (
    <div className="space-y-6">
      {/* Current Fundamentals Card */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">현재 펀더멘털</h3>
        {error || !fundamental ? (
          <div className="flex items-center gap-2 text-amber-600">
            <AlertCircle className="w-5 h-5" />
            <span>펀더멘털 데이터를 불러올 수 없습니다.</span>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {fundamentalFields.map((field) => {
                const value = fundamental[field.key as keyof typeof fundamental];
                return (
                  <div key={field.key} className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                    <div className="text-xs text-slate-500 mb-1">{field.label}</div>
                    <div className="text-xl font-bold text-slate-800">
                      {field.format(value as number | null)}
                      {value != null && (
                        <span className="text-sm font-normal text-slate-500 ml-1">{field.unit}</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="text-xs text-slate-400 pt-3 border-t">
              기준일: {fundamental.trade_date}
            </div>
          </div>
        )}
      </div>

      {/* Key Ratios Display */}
      {fundamental && (
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">주요 밸류에이션 지표</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* PER Analysis */}
            <div className="space-y-3">
              <div className="text-sm font-medium text-slate-700">주가수익비율 (PER)</div>
              <div className="text-3xl font-bold text-slate-800">
                {fundamental.per != null ? fundamental.per.toFixed(2) : "-"}
                <span className="text-lg font-normal text-slate-500 ml-1">배</span>
              </div>
              <div className="text-xs text-slate-600">
                {fundamental.per != null ? (
                  <>
                    {fundamental.per < 0 ? (
                      <span className="text-red-600">음수 (적자 상태)</span>
                    ) : fundamental.per < 10 ? (
                      <span className="text-green-600">저평가 (10배 미만)</span>
                    ) : fundamental.per < 20 ? (
                      <span className="text-blue-600">적정 (10~20배)</span>
                    ) : (
                      <span className="text-amber-600">고평가 (20배 이상)</span>
                    )}
                  </>
                ) : (
                  <span className="text-slate-400">데이터 없음</span>
                )}
              </div>
              <div className="text-xs text-slate-500 pt-2 border-t">
                낮을수록 주가가 저평가되어 있음을 의미합니다. 업종별 평균 PER과 비교하여 판단해야 합니다.
              </div>
            </div>

            {/* PBR Analysis */}
            <div className="space-y-3">
              <div className="text-sm font-medium text-slate-700">주가순자산비율 (PBR)</div>
              <div className="text-3xl font-bold text-slate-800">
                {fundamental.pbr != null ? fundamental.pbr.toFixed(2) : "-"}
                <span className="text-lg font-normal text-slate-500 ml-1">배</span>
              </div>
              <div className="text-xs text-slate-600">
                {fundamental.pbr != null ? (
                  <>
                    {fundamental.pbr < 1 ? (
                      <span className="text-green-600">저평가 (1배 미만)</span>
                    ) : fundamental.pbr < 2 ? (
                      <span className="text-blue-600">적정 (1~2배)</span>
                    ) : (
                      <span className="text-amber-600">고평가 (2배 이상)</span>
                    )}
                  </>
                ) : (
                  <span className="text-slate-400">데이터 없음</span>
                )}
              </div>
              <div className="text-xs text-slate-500 pt-2 border-t">
                1배 미만이면 주가가 장부가치보다 낮아 저평가 신호로 해석됩니다. 성장주는 PBR이 높을 수 있습니다.
              </div>
            </div>

            {/* ROE Analysis */}
            <div className="space-y-3">
              <div className="text-sm font-medium text-slate-700">자기자본이익률 (ROE)</div>
              <div className="text-3xl font-bold text-slate-800">
                {fundamental.roe != null ? fundamental.roe.toFixed(2) : "-"}
                <span className="text-lg font-normal text-slate-500 ml-1">%</span>
              </div>
              <div className="text-xs text-slate-600">
                {fundamental.roe != null ? (
                  <>
                    {fundamental.roe < 0 ? (
                      <span className="text-red-600">적자 (음수)</span>
                    ) : fundamental.roe < 5 ? (
                      <span className="text-amber-600">낮음 (5% 미만)</span>
                    ) : fundamental.roe < 10 ? (
                      <span className="text-blue-600">보통 (5~10%)</span>
                    ) : fundamental.roe < 15 ? (
                      <span className="text-green-600">우수 (10~15%)</span>
                    ) : (
                      <span className="text-emerald-600">매우 우수 (15% 이상)</span>
                    )}
                  </>
                ) : (
                  <span className="text-slate-400">데이터 없음</span>
                )}
              </div>
              <div className="text-xs text-slate-500 pt-2 border-t">
                자기자본 대비 수익률로, 높을수록 경영 효율성이 우수함을 의미합니다. 일반적으로 10% 이상이 양호합니다.
              </div>
            </div>

            {/* Dividend Analysis */}
            <div className="space-y-3">
              <div className="text-sm font-medium text-slate-700">배당수익률 (DIV)</div>
              <div className="text-3xl font-bold text-slate-800">
                {fundamental.div != null ? fundamental.div.toFixed(2) : "-"}
                <span className="text-lg font-normal text-slate-500 ml-1">%</span>
              </div>
              <div className="text-xs text-slate-600">
                {fundamental.div != null ? (
                  <>
                    {fundamental.div === 0 ? (
                      <span className="text-slate-400">무배당</span>
                    ) : fundamental.div < 2 ? (
                      <span className="text-slate-600">낮음 (2% 미만)</span>
                    ) : fundamental.div < 4 ? (
                      <span className="text-blue-600">보통 (2~4%)</span>
                    ) : (
                      <span className="text-green-600">높음 (4% 이상)</span>
                    )}
                  </>
                ) : (
                  <span className="text-slate-400">데이터 없음</span>
                )}
              </div>
              <div className="text-xs text-slate-500 pt-2 border-t">
                주가 대비 배당금 비율로, 높을수록 배당 매력이 큽니다. 예금 금리와 비교하여 투자 판단에 활용합니다.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Fundamentals Note */}
      <div className="bg-slate-50 rounded-lg border border-slate-200 p-6">
        <h3 className="text-sm font-semibold text-slate-800 mb-2">펀더멘털 지표 해석 가이드</h3>
        <div className="text-sm text-slate-600 space-y-2">
          <p>
            펀더멘털 지표는 기업의 재무 건전성과 수익성을 평가하는 핵심 지표입니다. 각 지표를 종합적으로 판단하여
            투자 결정에 활용하세요.
          </p>
          <ul className="list-disc list-inside space-y-1 text-xs">
            <li>
              <strong>PER/PBR:</strong> 밸류에이션 지표 - 업종 평균과 비교하여 저평가/고평가 판단
            </li>
            <li>
              <strong>ROE:</strong> 수익성 지표 - 10% 이상이면 양호, 15% 이상이면 우수
            </li>
            <li>
              <strong>DIV:</strong> 배당 매력 지표 - 배당주 투자 시 중요, 4% 이상이면 고배당
            </li>
            <li>
              <strong>BPS/EPS:</strong> 기본 재무 지표 - 시간에 따른 증가 추세가 중요
            </li>
          </ul>
          <p className="text-xs text-slate-500 pt-2 border-t">
            <strong>주의:</strong> 단일 지표만으로 판단하지 말고, 여러 지표를 종합적으로 분석하세요. 업종 특성과 기업의
            성장 단계를 고려해야 합니다.
          </p>
        </div>
      </div>
    </div>
  );
}
