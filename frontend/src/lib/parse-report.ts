import type { ParsedReportSection } from "@/types/api";

const SECTION_ID_MAP: Record<string, string> = {
  "핵심 요약": "executive-summary",
  "시장 환경": "market-environment",
  "기관/외국인 수급 분석": "institutional-flow",
  "섹터 로테이션 및 테마 분석": "sector-rotation",
  "종목 스포트라이트": "stock-spotlight",
  "퀀트 시그널 리뷰": "quant-signal",
  "추세/모멘텀 분석": "trend-momentum",
  "뉴스 감성 영향 분석": "news-sentiment",
  "리스크 평가": "risk-assessment",
  "이전 리포트 비교 및 정확도": "previous-comparison",
  "전략적 제언": "strategy",
  "관심 종목 리스트": "watchlist",
};

export function parseReportSections(
  fullReport: string
): ParsedReportSection[] {
  if (!fullReport) return [];

  const lines = fullReport.split("\n");
  const sections: ParsedReportSection[] = [];
  let currentTitle = "";
  let currentContent: string[] = [];
  let currentLevel = 1;

  for (const line of lines) {
    const h2Match = line.match(/^##\s+(.+)$/);
    if (h2Match) {
      if (currentTitle) {
        sections.push({
          id: SECTION_ID_MAP[currentTitle] || slugify(currentTitle),
          title: currentTitle,
          content: currentContent.join("\n").trim(),
          level: currentLevel,
        });
      }
      currentTitle = h2Match[1].trim();
      currentContent = [];
      currentLevel = 1;
      continue;
    }
    if (currentTitle) {
      currentContent.push(line);
    }
  }

  if (currentTitle) {
    sections.push({
      id: SECTION_ID_MAP[currentTitle] || slugify(currentTitle),
      title: currentTitle,
      content: currentContent.join("\n").trim(),
      level: currentLevel,
    });
  }

  return sections;
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9가-힣\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .trim();
}

export const REPORT_SECTIONS = [
  { id: "executive-summary", title: "핵심 요약", subtitle: "Executive Summary" },
  { id: "market-environment", title: "시장 환경", subtitle: "Market Environment" },
  { id: "institutional-flow", title: "기관/외국인 수급 분석", subtitle: "Institutional Flow" },
  { id: "sector-rotation", title: "섹터 로테이션 및 테마 분석", subtitle: "Sector Rotation" },
  { id: "stock-spotlight", title: "종목 스포트라이트", subtitle: "Stock Spotlight" },
  { id: "quant-signal", title: "퀀트 시그널 리뷰", subtitle: "Quant Signal" },
  { id: "trend-momentum", title: "추세/모멘텀 분석", subtitle: "Trend & Momentum" },
  { id: "news-sentiment", title: "뉴스 감성 영향 분석", subtitle: "News Sentiment" },
  { id: "risk-assessment", title: "리스크 평가", subtitle: "Risk Assessment" },
  { id: "previous-comparison", title: "이전 리포트 비교 및 정확도", subtitle: "Previous Comparison" },
  { id: "strategy", title: "전략적 제언", subtitle: "Strategic Recommendations" },
  { id: "watchlist", title: "관심 종목 리스트", subtitle: "Watchlist" },
];
