"use client";

import { useNewsSentiment } from "@/lib/queries";
import { cn } from "@/lib/utils";

const SIGNAL_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  strong_buy: { label: "강력 매수", color: "text-red-700", bg: "bg-red-50 border-red-200" },
  buy: { label: "매수", color: "text-red-600", bg: "bg-red-50 border-red-100" },
  neutral: { label: "중립", color: "text-slate-600", bg: "bg-slate-50 border-slate-200" },
  sell: { label: "매도", color: "text-blue-600", bg: "bg-blue-50 border-blue-100" },
  strong_sell: { label: "강력 매도", color: "text-blue-700", bg: "bg-blue-50 border-blue-200" },
};

const STATUS_LABELS: Record<string, string> = {
  active: "활성",
  stale: "오래됨",
  insufficient: "기사 부족",
  no_data: "데이터 없음",
};

function ScoreBar({ value, max = 100, label }: { value: number | null; max?: number; label: string }) {
  if (value === null || value === undefined) return null;
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-slate-600">{label}</span>
        <span className="font-medium text-slate-900">{value.toFixed(1)}</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-blue-500 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function NewsTab({ ticker }: { ticker: string }) {
  const { data, isLoading, error } = useNewsSentiment(ticker);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse space-y-4">
          <div className="h-32 bg-slate-200 rounded-lg" />
          <div className="h-48 bg-slate-200 rounded-lg" />
        </div>
      </div>
    );
  }

  if (error || !data?.data) {
    return (
      <div className="bg-slate-50 border border-slate-200 rounded-lg p-8 text-center">
        <p className="text-slate-500">뉴스 감성 분석 데이터가 없습니다</p>
        <p className="text-sm text-slate-400 mt-1">분석이 아직 실행되지 않았거나 뉴스 데이터가 부족합니다</p>
      </div>
    );
  }

  const news = data.data;
  const signal = SIGNAL_CONFIG[news.sentiment_signal || "neutral"] || SIGNAL_CONFIG.neutral;
  const statusLabel = STATUS_LABELS[news.status || "no_data"] || news.status;

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className={cn("rounded-lg border p-6", signal.bg)}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-500 mb-1">뉴스 감성 시그널</p>
            <p className={cn("text-2xl font-bold", signal.color)}>{signal.label}</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-slate-500 mb-1">감성 점수</p>
            <p className="text-3xl font-bold text-slate-900">
              {news.sentiment_score !== null ? news.sentiment_score.toFixed(1) : "-"}
            </p>
            <p className="text-xs text-slate-400">/ 100</p>
          </div>
        </div>
        <div className="mt-4 flex items-center gap-4 text-sm text-slate-500">
          <span>분석 기사: {news.article_count ?? 0}건</span>
          <span>상태: {statusLabel}</span>
          <span>기준일: {news.trade_date}</span>
        </div>
      </div>

      {/* 3-Dimensional Decomposition */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">감성 3차원 분해</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="space-y-2">
            <div className="flex justify-between items-baseline">
              <span className="text-sm font-medium text-slate-700">방향 (Direction)</span>
              <span className={cn(
                "text-lg font-bold",
                (news.direction ?? 0) > 0 ? "text-red-600" : (news.direction ?? 0) < 0 ? "text-blue-600" : "text-slate-600"
              )}>
                {news.direction !== null ? (news.direction > 0 ? "+" : "") + news.direction.toFixed(3) : "-"}
              </span>
            </div>
            <p className="text-xs text-slate-400">감성 방향 및 크기 [-1, +1]</p>
            <div className="h-3 bg-slate-100 rounded-full overflow-hidden relative">
              <div className="absolute inset-0 flex">
                <div className="w-1/2 flex justify-end">
                  {(news.direction ?? 0) < 0 && (
                    <div
                      className="h-full bg-blue-400 rounded-l-full"
                      style={{ width: `${Math.abs(news.direction ?? 0) * 100}%` }}
                    />
                  )}
                </div>
                <div className="w-px bg-slate-300" />
                <div className="w-1/2">
                  {(news.direction ?? 0) > 0 && (
                    <div
                      className="h-full bg-red-400 rounded-r-full"
                      style={{ width: `${Math.abs(news.direction ?? 0) * 100}%` }}
                    />
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <ScoreBar value={news.intensity !== null ? news.intensity * 100 : null} label="강도 (Intensity)" />
            <p className="text-xs text-slate-400">반응 강도 (기사 수 반영) [0, 1]</p>
          </div>

          <div className="space-y-2">
            <ScoreBar value={news.confidence !== null ? news.confidence * 100 : null} label="신뢰도 (Confidence)" />
            <p className="text-xs text-slate-400">기사 간 합의도 [0, 1]</p>
          </div>
        </div>

        {/* Effective Score */}
        <div className="mt-6 pt-4 border-t border-slate-100">
          <div className="flex justify-between items-baseline">
            <span className="text-sm font-medium text-slate-700">유효 점수 (Effective Score)</span>
            <span className={cn(
              "text-xl font-bold",
              (news.effective_score ?? 0) > 0.15 ? "text-red-600" :
              (news.effective_score ?? 0) < -0.15 ? "text-blue-600" : "text-slate-600"
            )}>
              {news.effective_score !== null ? (news.effective_score > 0 ? "+" : "") + news.effective_score.toFixed(4) : "-"}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">S_eff = 방향 × 강도 × 신뢰도 (시뮬레이션 모델 조정에 사용)</p>
        </div>
      </div>

      {/* Source Breakdown */}
      {news.source_breakdown && Object.keys(news.source_breakdown).length > 0 && (() => {
        const entries = Object.entries(news.source_breakdown)
          .map(([source, count]) => [source.replace(/^www\./, ""), count as number] as const)
          .sort((a, b) => b[1] - a[1]);
        const top = entries.slice(0, 12);
        const rest = entries.slice(12);
        const restCount = rest.reduce((sum, [, c]) => sum + c, 0);

        return (
          <div className="bg-white rounded-lg border border-slate-200 p-6">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">소스별 기사 수</h3>
            <div className="flex flex-wrap gap-2">
              {top.map(([source, count]) => (
                <div key={source} className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-50 rounded-md border border-slate-100">
                  <span className="text-xs text-slate-500 truncate max-w-[140px]">{source}</span>
                  <span className="text-xs font-semibold text-slate-700">{count}</span>
                </div>
              ))}
              {restCount > 0 && (
                <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-100 rounded-md border border-slate-200">
                  <span className="text-xs text-slate-500">기타 {rest.length}개 소스</span>
                  <span className="text-xs font-semibold text-slate-700">{restCount}</span>
                </div>
              )}
            </div>
          </div>
        );
      })()}

      {/* Info Card */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
        <p className="text-sm text-amber-800">
          <span className="font-medium">AI 뉴스 감성 분석</span> — 네이버 뉴스 + DART 공시를 수집하여
          BERT 모델(KLUE-RoBERTa)과 LLM을 활용한 하이브리드 감성 분석 결과입니다.
          감성 점수는 몬테카를로 시뮬레이션의 드리프트·변동성·앙상블 가중치 조정에 반영됩니다.
        </p>
      </div>
    </div>
  );
}
