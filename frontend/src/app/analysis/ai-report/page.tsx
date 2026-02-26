"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useMemo, useCallback, Suspense } from "react";
import {
  useMarketSummary,
  useMarketSummaryByDate,
  useMarketSummaryHistory,
} from "@/lib/queries";
import { parseReportSections, REPORT_SECTIONS } from "@/lib/parse-report";
import { useScrollSpy } from "@/hooks/use-scroll-spy";
import ReportHeader from "@/components/report/report-header";
import ReportTOCSidebar from "@/components/report/report-toc-sidebar";
import ReportTOCMobile from "@/components/report/report-toc-mobile";
import ReportSection from "@/components/report/report-section";
import ReportFooter from "@/components/report/report-footer";
import ReportSectionContent from "@/components/report/report-section-content";
import AIReportLoading from "./loading";
import type { MarketSummaryHistoryItem } from "@/types/api";

function AIReportInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const selectedDate = searchParams.get("date");

  const { data: latestData, isLoading: latestLoading } = useMarketSummary();
  const { data: dateData, isLoading: dateLoading } = useMarketSummaryByDate(selectedDate);
  const { data: historyData } = useMarketSummaryHistory(60);

  const isLoading = selectedDate ? dateLoading : latestLoading;
  const rawSummary = selectedDate ? dateData?.data : latestData?.data;
  const summary = rawSummary ?? null;

  const sections = useMemo(
    () => (summary?.full_report ? parseReportSections(summary.full_report) : []),
    [summary?.full_report]
  );

  const sectionIds = useMemo(() => sections.map((s) => s.id), [sections]);
  const activeId = useScrollSpy(sectionIds);

  const availableDates = useMemo(() => {
    const items = historyData?.data ?? [];
    return items.map((item: MarketSummaryHistoryItem) => item.trade_date);
  }, [historyData]);

  const handleDateChange = useCallback(
    (date: string) => {
      router.push(`/analysis/ai-report?date=${date}`);
    },
    [router]
  );

  const handleScrollTo = useCallback((id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  if (isLoading) return <AIReportLoading />;

  if (!summary) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-violet-50">
          <svg
            className="h-8 w-8 text-violet-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
            />
          </svg>
        </div>
        <h2 className="text-lg font-semibold text-slate-900">리포트가 없습니다</h2>
        <p className="mt-2 text-sm text-slate-500">
          compute-analysis 실행 후 AI 리포트가 생성됩니다.
        </p>
      </div>
    );
  }

  const currentDate = summary.trade_date;

  const accentColors: Record<string, string> = {
    "executive-summary": "border-violet-400",
    "market-environment": "border-slate-300",
    "institutional-flow": "border-blue-400",
    "sector-rotation": "border-emerald-400",
    "stock-spotlight": "border-amber-400",
    "quant-signal": "border-blue-400",
    "trend-momentum": "border-cyan-400",
    "news-sentiment": "border-purple-400",
    "risk-assessment": "border-red-400",
    "previous-comparison": "border-slate-400",
    "strategy": "border-blue-500",
    "watchlist": "border-violet-400",
  };

  return (
    <div>
      <ReportHeader
        currentDate={currentDate}
        availableDates={availableDates}
        onDateChange={handleDateChange}
        modelUsed={summary.model_used}
      />

      <ReportTOCMobile
        sections={sections}
        activeId={activeId}
        onScrollTo={handleScrollTo}
      />

      <div className="flex gap-8">
        <ReportTOCSidebar
          sections={sections}
          activeId={activeId}
          onScrollTo={handleScrollTo}
        />

        <div className="min-w-0 flex-1 max-w-3xl">
          {sections.map((section, index) => (
            <ReportSection
              key={section.id}
              id={section.id}
              sectionNumber={index + 1}
              title={section.title}
              subtitle={REPORT_SECTIONS.find((s) => s.id === section.id)?.subtitle}
              accentColor={accentColors[section.id] || "border-slate-300"}
            >
              <ReportSectionContent
                sectionId={section.id}
                content={section.content}
                keyInsights={summary.key_insights}
                sectorHighlights={summary.sector_highlights}
              />
            </ReportSection>
          ))}

          <ReportFooter
            modelUsed={summary.model_used}
            condenserModelUsed={summary.condenser_model_used}
            computedAt={summary.computed_at}
            tradeDate={summary.trade_date}
          />
        </div>
      </div>
    </div>
  );
}

export default function AIReportPage() {
  return (
    <Suspense fallback={<AIReportLoading />}>
      <AIReportInner />
    </Suspense>
  );
}
