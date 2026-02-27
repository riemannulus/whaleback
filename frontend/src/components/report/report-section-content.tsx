"use client";

import type {
  MarketSummaryKeyInsights,
  MarketSummarySectorHighlight,
} from "@/types/api";

interface ReportSectionContentProps {
  sectionId: string;
  content: string;
  keyInsights: MarketSummaryKeyInsights | null;
  sectorHighlights: Record<string, MarketSummarySectorHighlight> | null;
}

function formatInline(text: string): string {
  return text
    .replace(
      /\*\*(.+?)\*\*/g,
      '<strong class="font-semibold text-slate-900">$1</strong>'
    )
    .replace(/\*(.+?)\*/g, "<em>$1</em>");
}

function MarkdownContent({ text }: { text: string }) {
  if (!text) return null;

  const lines = text.split("\n");

  return (
    <div className="space-y-2">
      {lines.map((line, i) => {
        const trimmed = line.trim();
        if (!trimmed) return <div key={i} className="h-2" />;

        if (trimmed.startsWith("- ") || trimmed.startsWith("• ")) {
          const bulletText = trimmed.replace(/^[-•]\s*/, "");
          return (
            <div
              key={i}
              className="flex items-start gap-2.5 text-sm text-slate-700 leading-relaxed"
            >
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-400" />
              <span
                dangerouslySetInnerHTML={{ __html: formatInline(bulletText) }}
              />
            </div>
          );
        }

        if (trimmed.startsWith("### ")) {
          return (
            <h3
              key={i}
              className="mt-4 mb-2 text-base font-semibold text-slate-800"
            >
              {trimmed.replace(/^###\s*/, "")}
            </h3>
          );
        }

        return (
          <p
            key={i}
            className="text-sm text-slate-700 leading-relaxed"
            dangerouslySetInnerHTML={{ __html: formatInline(trimmed) }}
          />
        );
      })}
    </div>
  );
}

function ExecutiveSummaryContent({
  content,
  keyInsights,
}: {
  content: string;
  keyInsights: MarketSummaryKeyInsights | null;
}) {
  const overview =
    keyInsights?.market_overview ?? keyInsights?.executive_summary;

  return (
    <div>
      {overview && (
        <div className="mb-4 border-l-4 border-violet-300 pl-4 text-base font-medium leading-relaxed text-slate-800">
          {overview}
        </div>
      )}
      <MarkdownContent text={content} />
    </div>
  );
}

function RiskAssessmentContent({
  content,
  keyInsights,
}: {
  content: string;
  keyInsights: MarketSummaryKeyInsights | null;
}) {
  const riskText =
    keyInsights?.risk_factors ?? keyInsights?.risk_assessment;

  return (
    <div>
      {riskText && (
        <div className="mb-4 flex gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <svg
            className="mt-0.5 h-5 w-5 shrink-0 text-amber-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
            />
          </svg>
          <p className="text-sm leading-relaxed text-amber-900">{riskText}</p>
        </div>
      )}
      <MarkdownContent text={content} />
    </div>
  );
}

function StrategyContent({
  content,
  keyInsights,
}: {
  content: string;
  keyInsights: MarketSummaryKeyInsights | null;
}) {
  const strategyText = keyInsights?.strategy;

  return (
    <div>
      {strategyText && (
        <div className="mb-4 flex gap-3 rounded-lg border border-blue-100 bg-gradient-to-br from-blue-50 to-violet-50 p-5">
          <svg
            className="mt-0.5 h-5 w-5 shrink-0 text-blue-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18"
            />
          </svg>
          <p className="text-sm leading-relaxed text-slate-800">{strategyText}</p>
        </div>
      )}
      <MarkdownContent text={content} />
    </div>
  );
}

function StockSpotlightContent({
  content,
}: {
  content: string;
  keyInsights: MarketSummaryKeyInsights | null;
}) {
  return <MarkdownContent text={content} />;
}

function SectorRotationContent({
  content,
  sectorHighlights,
}: {
  content: string;
  sectorHighlights: Record<string, MarketSummarySectorHighlight> | null;
}) {
  return (
    <div>
      {sectorHighlights && Object.keys(sectorHighlights).length > 0 && (
        <div className="mb-4 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {Object.entries(sectorHighlights)
            .sort(([, a], [, b]) => Math.abs(b.net_purchase) - Math.abs(a.net_purchase))
            .slice(0, 9)
            .map(([sector, data]) => (
              <div
                key={sector}
                className="rounded-lg border border-slate-100 bg-slate-50 p-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-700">
                    {sector}
                  </span>
                  <span
                    className={`text-xs font-medium ${
                      data.net_purchase > 0 ? "text-red-600" : "text-blue-600"
                    }`}
                  >
                    {data.net_purchase > 0 ? "+" : ""}
                    {data.net_purchase.toFixed(0)}억
                  </span>
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  {data.signal} · {data.key_investors.slice(0, 2).join(", ")}
                </div>
              </div>
            ))}
        </div>
      )}
      <MarkdownContent text={content} />
    </div>
  );
}

export default function ReportSectionContent({
  sectionId,
  content,
  keyInsights,
  sectorHighlights,
}: ReportSectionContentProps) {
  switch (sectionId) {
    case "executive-summary":
      return (
        <ExecutiveSummaryContent content={content} keyInsights={keyInsights} />
      );
    case "risk-assessment":
      return (
        <RiskAssessmentContent content={content} keyInsights={keyInsights} />
      );
    case "strategy":
      return (
        <StrategyContent content={content} keyInsights={keyInsights} />
      );
    case "stock-spotlight":
      return (
        <StockSpotlightContent content={content} keyInsights={keyInsights} />
      );
    case "sector-rotation":
      return (
        <SectorRotationContent
          content={content}
          sectorHighlights={sectorHighlights}
        />
      );
    default:
      return <MarkdownContent text={content} />;
  }
}
