"use client";

import Link from "next/link";
import { useMarketSummary } from "@/lib/queries";

function MarkdownBullets({ text }: { text: string }) {
  const lines = text
    .split("\n")
    .map((l) => l.replace(/^[-•]\s*/, "").trim())
    .filter(Boolean);

  return (
    <ul className="space-y-2">
      {lines.map((line, i) => (
        <li key={i} className="flex items-start gap-2.5 text-sm text-slate-700">
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-violet-400" />
          <span
            dangerouslySetInnerHTML={{
              __html: line.replace(
                /\*\*(.+?)\*\*/g,
                '<strong class="font-semibold text-slate-900">$1</strong>'
              ),
            }}
          />
        </li>
      ))}
    </ul>
  );
}

export default function MarketAISummary() {
  const { data, isLoading, isError } = useMarketSummary();
  const summary = data?.data ?? null;

  return (
    <div className="rounded-lg border border-violet-100 bg-white p-5 shadow-sm">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-50">
            <svg className="h-4.5 w-4.5 text-violet-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <h2 className="text-base font-semibold text-slate-900">시장 AI 요약</h2>
          {summary && (
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
              {summary.trade_date}
            </span>
          )}
        </div>
        <Link
          href="/analysis/ai-report"
          className="inline-flex items-center gap-1 text-sm font-medium text-violet-600 hover:text-violet-800 transition-colors"
        >
          자세히 보기
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </Link>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-4 animate-pulse rounded bg-slate-100" style={{ width: `${85 - i * 10}%` }} />
          ))}
        </div>
      ) : isError || !summary ? (
        <p className="text-sm text-slate-400">
          시장 분석 데이터가 아직 없습니다. compute-analysis 실행 후 표시됩니다.
        </p>
      ) : (
        <MarkdownBullets text={summary.dashboard_summary} />
      )}
    </div>
  );
}
