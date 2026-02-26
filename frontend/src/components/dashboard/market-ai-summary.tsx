"use client";

import { useState } from "react";
import { useMarketSummary } from "@/lib/queries";
import type { MarketSummary } from "@/types/api";

// Simple inline markdown renderer (bullet points + bold only, no dangerouslySetInnerHTML)
function MarkdownBullets({ text }: { text: string }) {
  const lines = text.split("\n").filter((l) => l.trim().length > 0);

  return (
    <ul className="space-y-1.5">
      {lines.map((line, i) => {
        const clean = line.replace(/^[-*•]\s*/, "").trim();
        // Bold: **text**
        const parts = clean.split(/(\*\*[^*]+\*\*)/g);
        return (
          <li key={i} className="flex gap-2 text-sm text-slate-700">
            <span className="mt-1 flex-shrink-0 w-1.5 h-1.5 rounded-full bg-violet-400" />
            <span>
              {parts.map((part, j) =>
                part.startsWith("**") && part.endsWith("**") ? (
                  <strong key={j}>{part.slice(2, -2)}</strong>
                ) : (
                  part
                )
              )}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function InsightCard({
  icon,
  title,
  content,
}: {
  icon: React.ReactNode;
  title: string;
  content: string;
}) {
  return (
    <div className="p-3 rounded-lg border border-slate-100 bg-slate-50">
      <div className="flex items-center gap-1.5 mb-1.5">
        <span className="text-violet-600">{icon}</span>
        <span className="text-xs font-semibold text-slate-600">{title}</span>
      </div>
      <p className="text-sm text-slate-700 leading-snug line-clamp-3">{content}</p>
    </div>
  );
}

function SkeletonBlock({ className }: { className?: string }) {
  return <div className={`bg-slate-100 animate-pulse rounded ${className}`} />;
}

function SummaryContent({ summary }: { summary: MarketSummary }) {
  const [expanded, setExpanded] = useState(false);
  const insights = summary.key_insights;

  return (
    <div className="space-y-5">
      {/* Dashboard summary */}
      <div>
        <MarkdownBullets text={summary.dashboard_summary} />
      </div>

      {/* Key insight cards */}
      {insights && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <InsightCard
            icon={
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
              </svg>
            }
            title="기관 동향"
            content={insights.institutional_moves}
          />
          <InsightCard
            icon={
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            }
            title="섹터 로테이션"
            content={insights.sector_rotation}
          />
          <InsightCard
            icon={
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            }
            title="전략"
            content={insights.strategy}
          />
          <InsightCard
            icon={
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            }
            title="리스크"
            content={insights.risk_factors}
          />
        </div>
      )}

      {/* Full report toggle */}
      <div>
        <button
          onClick={() => setExpanded((v) => !v)}
          className="text-sm text-violet-600 hover:text-violet-800 font-medium flex items-center gap-1"
        >
          <svg
            className={`w-4 h-4 transition-transform ${expanded ? "rotate-90" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
          {expanded ? "상세 리포트 접기" : "상세 리포트 보기"}
        </button>
        {expanded && (
          <div className="mt-3 p-4 rounded-lg bg-slate-50 border border-slate-200">
            <pre className="text-sm text-slate-700 whitespace-pre-wrap font-sans leading-relaxed">
              {summary.full_report}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

export function MarketAISummary() {
  const { data, isLoading, isError } = useMarketSummary();
  const summary: MarketSummary | null = data?.data ?? null;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-violet-100 p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-violet-100">
            <svg
              className="w-4 h-4 text-violet-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-slate-900">시장 AI 요약</h2>
        </div>
        {summary && (
          <span className="text-xs text-slate-400">{summary.trade_date} 기준</span>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <SkeletonBlock className="h-4 w-3/4" />
          <SkeletonBlock className="h-4 w-5/6" />
          <SkeletonBlock className="h-4 w-2/3" />
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-4">
            <SkeletonBlock className="h-24" />
            <SkeletonBlock className="h-24" />
            <SkeletonBlock className="h-24" />
            <SkeletonBlock className="h-24" />
          </div>
        </div>
      ) : isError || !summary ? (
        <div className="flex items-center justify-center h-24 text-sm text-slate-400">
          아직 시장 분석이 생성되지 않았습니다
        </div>
      ) : (
        <SummaryContent summary={summary} />
      )}
    </div>
  );
}
