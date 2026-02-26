"""Market AI Summary — LLM-powered market analysis report generation.

Generates daily market analysis reports using Anthropic Claude:
  1. Full report (Opus) — deep quant-trader perspective analysis
  2. Dashboard summary (Haiku) — condensed bullet-point highlights

Sync client only (compute pipeline is synchronous).
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class MarketSummaryInput:
    """시장 요약 생성에 필요한 입력 데이터."""

    trade_date: str  # YYYY-MM-DD
    sector_flows: list[dict[str, Any]]  # 섹터별 투자자 유형별 수급
    whale_top: list[dict[str, Any]]  # 수급 상위 종목
    trend_data: list[dict[str, Any]]  # 추세 데이터
    news_data: dict[str, Any]  # 뉴스 감성 집계
    composite_top: list[dict[str, Any]]  # 복합점수 상위
    composite_bottom: list[dict[str, Any]]  # 복합점수 하위
    market_stats: dict[str, Any]  # 시장 통계
    flow_data: list[dict[str, Any]]  # 수급 분석 데이터


@dataclass
class MarketReportResult:
    """시장 리포트 생성 결과."""

    full_report: str
    key_insights: dict[str, Any]
    sector_highlights: dict[str, Any]
    model_used: str
    input_tokens: int
    output_tokens: int


@dataclass
class DashboardSummaryResult:
    """대시보드 요약 결과."""

    summary: str
    model_used: str
    input_tokens: int
    output_tokens: int


# ---------------------------------------------------------------------------
# Anthropic client (sync, lazy singleton)
# ---------------------------------------------------------------------------

_client = None
_client_api_key: str | None = None


def _get_client(api_key: str):
    """Lazy-load Anthropic sync client (singleton)."""
    global _client, _client_api_key
    if _client is not None and _client_api_key == api_key:
        return _client
    import anthropic

    _client = anthropic.Anthropic(api_key=api_key, max_retries=3)
    _client_api_key = api_key
    return _client


# ---------------------------------------------------------------------------
# Investor type label mapping (reuse from sector_flow)
# ---------------------------------------------------------------------------

_INVESTOR_LABELS = {
    "institution_net": "기관",
    "foreign_net": "외국인",
    "pension_net": "연기금",
    "private_equity_net": "사모펀드",
    "other_corp_net": "기타법인",
}

# ---------------------------------------------------------------------------
# Report section parsing
# ---------------------------------------------------------------------------

_SECTION_KEY_MAP = {
    "시장 개요": "market_overview",
    "기관 동향 분석": "institutional_moves",
    "섹터 로테이션": "sector_rotation",
    "주목할 종목": "notable_stocks",
    "리스크 요인": "risk_factors",
    "이전 대비 변화": "previous_changes",
    "전략적 시사점": "strategy",
}


def _parse_report_sections(report: str) -> dict[str, Any]:
    """Parse markdown report into key_insights by ## section headers."""
    sections: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    for line in report.split("\n"):
        header_match = re.match(r"^##\s+\d*\.?\s*(.+)", line)
        if header_match:
            # Save previous section
            if current_key is not None:
                sections[current_key] = "\n".join(current_lines).strip()
            # Map header to key
            header_text = header_match.group(1).strip()
            current_key = None
            for kr_key, en_key in _SECTION_KEY_MAP.items():
                if kr_key in header_text:
                    current_key = en_key
                    break
            if current_key is None:
                # Fallback: use sanitized header
                current_key = re.sub(r"[^a-zA-Z가-힣0-9]", "_", header_text).strip("_").lower()
            current_lines = []
        elif current_key is not None:
            current_lines.append(line)

    # Save last section
    if current_key is not None:
        sections[current_key] = "\n".join(current_lines).strip()

    # Build key_insights: 1-2 sentence summary per section
    key_insights: dict[str, Any] = {}
    for key, content in sections.items():
        if key == "notable_stocks":
            # Extract stock names/tickers from bullet points
            stocks = []
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith(("-", "*", "•")):
                    # Take first meaningful chunk (stock name)
                    clean = re.sub(r"^[-*•]\s*", "", line)
                    # Extract bold text or first segment
                    bold_match = re.search(r"\*\*(.+?)\*\*", clean)
                    if bold_match:
                        stocks.append(bold_match.group(1))
                    elif clean:
                        stocks.append(clean.split(":")[0].split("(")[0].strip()[:30])
            key_insights[key] = stocks[:10]
        else:
            # Take first 1-2 non-empty lines as summary
            lines = [l.strip() for l in content.split("\n") if l.strip() and not l.strip().startswith("#")]
            summary_lines = []
            for l in lines:
                clean = re.sub(r"^[-*•]\s*", "", l)
                if clean:
                    summary_lines.append(clean)
                if len(summary_lines) >= 2:
                    break
            key_insights[key] = " ".join(summary_lines)[:200] if summary_lines else ""

    return key_insights


def _build_sector_highlights(sector_flows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build sector_highlights from sector flow data (no LLM needed)."""
    # Group by sector
    sector_map: dict[str, dict[str, Any]] = {}
    for flow in sector_flows:
        sector = flow.get("sector", "")
        if not sector:
            continue
        if sector not in sector_map:
            sector_map[sector] = {
                "signal": "neutral",
                "key_investors": [],
                "net_purchase": 0,
                "max_intensity": 0.0,
            }

        entry = sector_map[sector]
        inv_type = flow.get("investor_type", "")
        net = flow.get("net_purchase", 0)
        intensity = flow.get("intensity", 0.0)
        signal = flow.get("signal", "neutral")

        entry["net_purchase"] += net

        if intensity > entry["max_intensity"]:
            entry["max_intensity"] = intensity

        # Track which investors are active
        if abs(net) > 0 and inv_type in _INVESTOR_LABELS:
            entry["key_investors"].append(_INVESTOR_LABELS[inv_type])

        # Upgrade signal if stronger
        signal_rank = {
            "strong_accumulation": 3,
            "mild_accumulation": 2,
            "neutral": 1,
            "distribution": 0,
        }
        if signal_rank.get(signal, 1) > signal_rank.get(entry["signal"], 1):
            entry["signal"] = signal

    # Clean up
    highlights: dict[str, Any] = {}
    for sector, data in sector_map.items():
        highlights[sector] = {
            "signal": data["signal"],
            "key_investors": list(dict.fromkeys(data["key_investors"])),  # deduplicate, preserve order
            "net_purchase": data["net_purchase"],
        }

    return highlights


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """당신은 한국 주식시장 전문 퀀트 트레이더이자 기관투자 전략가입니다.
제공된 데이터를 분석하여 전문적인 시장 분석 리포트를 작성하십시오.

분석 원칙:
- 데이터에 기반한 객관적 분석 (추측 금지)
- 기관투자자 관점에서 의미 있는 시그널 해석
- 섹터 간 자금 흐름의 의미 파악
- 리스크 요인에 대한 솔직한 평가
- 실행 가능한 전략적 시사점 제시"""

_REPORT_STRUCTURE = """
다음 구조로 리포트를 작성하세요:

# 시장 분석 리포트 ({date})

## 1. 시장 개요
- 전체 시장 분위기, KOSPI/KOSDAQ 방향성

## 2. 기관 동향 분석
- 기관투자자(기관, 외국인, 연기금, 사모, 보험 등) 순매수 패턴
- "이들의 움직임이 의미하는 것" - 시장을 어떻게 바라보고 있는지 해석
- 기관 간 의견 차이 (예: 외국인 매수 vs 연기금 매도)

## 3. 섹터 로테이션
- 수급이 몰리는 섹터 / 빠지는 섹터
- 추세 상대강도 기반 섹터 모멘텀

## 4. 주목할 종목
- 복합점수 + 수급 + 추세가 모두 긍정적인 종목
- 기관 집중 매수 중인 종목

## 5. 리스크 요인
- 변동성 증가 섹터/종목
- 다이버전스 경고 (가치 vs 모멘텀 불일치)

{previous_section}

## {next_num}. 전략적 시사점
- 단기/중기 관점 투자 전략 제안
- 주목해야 할 이벤트/섹터
"""


def _build_user_prompt(data: MarketSummaryInput, previous_report: str | None = None) -> str:
    """Build the user prompt with all data sections."""
    has_previous = previous_report is not None and len(previous_report.strip()) > 0

    previous_section = ""
    next_num = 6
    if has_previous:
        previous_section = """## 6. 이전 대비 변화
- 시장 분위기 변화
- 기관 포지션 변화
- 새로운 트렌드"""
        next_num = 7

    structure = _REPORT_STRUCTURE.format(
        date=data.trade_date,
        previous_section=previous_section,
        next_num=next_num,
    )

    sections = [f"분석 기준일: {data.trade_date}\n{structure}\n"]

    # 1. Sector flows
    if data.sector_flows:
        sections.append("### 섹터 수급 현황")
        for flow in data.sector_flows[:60]:  # Cap to avoid token waste
            inv_label = _INVESTOR_LABELS.get(flow.get("investor_type", ""), flow.get("investor_type", ""))
            sections.append(
                f"- {flow.get('sector', '?')} | {inv_label}: "
                f"순매수 {flow.get('net_purchase', 0):,}원, "
                f"강도 {flow.get('intensity', 0):.3f}, "
                f"일관성 {flow.get('consistency', 0):.0%}, "
                f"신호 {flow.get('signal', 'neutral')}, "
                f"5일추세 {flow.get('trend_5d', 0):,}"
            )

    # 2. Whale top stocks
    if data.whale_top:
        sections.append("\n### 수급 분석 상위 종목 (whale_score 기준)")
        for w in data.whale_top[:20]:
            sections.append(
                f"- {w.get('ticker', '?')} {w.get('name', '')}: "
                f"whale_score={w.get('whale_score', 0):.1f}, "
                f"기관20d={w.get('institution_net_20d', 0):,}, "
                f"외국인20d={w.get('foreign_net_20d', 0):,}, "
                f"연기금20d={w.get('pension_net_20d', 0):,}, "
                f"신호={w.get('signal', 'neutral')}"
            )

    # 3. Trend data
    if data.trend_data:
        sections.append("\n### 추세 분석 (섹터별 상대강도)")
        for t in data.trend_data[:30]:
            sections.append(
                f"- {t.get('sector', '?')}: "
                f"RS_20d={t.get('rs_vs_kospi_20d', 0):.3f}, "
                f"RS_60d={t.get('rs_vs_kospi_60d', 0):.3f}, "
                f"RS_pct={t.get('rs_percentile', 0)}"
            )

    # 4. News sentiment
    if data.news_data:
        sections.append("\n### 뉴스 감성 집계")
        sections.append(json.dumps(data.news_data, ensure_ascii=False, default=str))

    # 5. Composite top/bottom
    if data.composite_top:
        sections.append("\n### 복합점수 상위 20")
        for c in data.composite_top[:20]:
            sections.append(
                f"- {c.get('ticker', '?')} {c.get('name', '')}: "
                f"종합={c.get('composite_score', 0):.1f}, "
                f"가치={c.get('value_score', '-')}, "
                f"수급={c.get('flow_score', '-')}, "
                f"모멘텀={c.get('momentum_score', '-')}, "
                f"전망={c.get('forecast_score', '-')}, "
                f"신호={c.get('action_label', '-')}"
            )

    if data.composite_bottom:
        sections.append("\n### 복합점수 하위 20")
        for c in data.composite_bottom[:20]:
            sections.append(
                f"- {c.get('ticker', '?')} {c.get('name', '')}: "
                f"종합={c.get('composite_score', 0):.1f}, "
                f"가치={c.get('value_score', '-')}, "
                f"수급={c.get('flow_score', '-')}, "
                f"모멘텀={c.get('momentum_score', '-')}, "
                f"전망={c.get('forecast_score', '-')}, "
                f"신호={c.get('action_label', '-')}"
            )

    # 6. Market stats
    if data.market_stats:
        sections.append("\n### 시장 통계")
        sections.append(json.dumps(data.market_stats, ensure_ascii=False, default=str))

    # 7. Flow data (divergence, shift signals)
    if data.flow_data:
        sections.append("\n### 수급 분석 데이터 (상위)")
        for f in data.flow_data[:20]:
            sections.append(
                f"- {f.get('ticker', '?')}: "
                f"divergence={f.get('divergence_signal', '-')}, "
                f"shift={f.get('shift_signal', '-')}, "
                f"smart_ratio={f.get('smart_ratio', 0):.3f}"
            )

    # 8. Previous report
    if has_previous:
        sections.append("\n### 이전 분석일 리포트 (비교용)")
        # Truncate to avoid token overflow
        truncated = previous_report[:3000] if previous_report else ""
        sections.append(truncated)

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def generate_market_report(
    data: MarketSummaryInput,
    api_key: str,
    previous_report: str | None = None,
) -> MarketReportResult:
    """Generate a full market analysis report using Claude Opus.

    Args:
        data: Aggregated market data for the analysis date.
        api_key: Anthropic API key.
        previous_report: Previous day's report text for comparison (optional).

    Returns:
        MarketReportResult with full report, key insights, and sector highlights.
    """
    model = "claude-opus-4-20250514"

    # Build sector highlights from raw data (no LLM needed)
    sector_highlights = _build_sector_highlights(data.sector_flows)

    try:
        client = _get_client(api_key)
        user_prompt = _build_user_prompt(data, previous_report)

        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        full_report = response.content[0].text.strip()
        key_insights = _parse_report_sections(full_report)

        return MarketReportResult(
            full_report=full_report,
            key_insights=key_insights,
            sector_highlights=sector_highlights,
            model_used=model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    except Exception as e:
        logger.error("Failed to generate market report: %s", e)
        return MarketReportResult(
            full_report="",
            key_insights={},
            sector_highlights=sector_highlights,
            model_used=model,
            input_tokens=0,
            output_tokens=0,
        )


def condense_for_dashboard(
    full_report: str,
    api_key: str,
) -> DashboardSummaryResult:
    """Condense a full market report into a dashboard-friendly summary.

    Uses Claude Haiku for cost efficiency (~$0.001/call).

    Args:
        full_report: The full markdown report from generate_market_report().
        api_key: Anthropic API key.

    Returns:
        DashboardSummaryResult with condensed markdown summary.
    """
    model = "claude-haiku-4-5-20251001"

    if not full_report:
        return DashboardSummaryResult(
            summary="",
            model_used=model,
            input_tokens=0,
            output_tokens=0,
        )

    prompt = f"""다음 시장 분석 리포트를 대시보드에 표시할 간결한 요약으로 변환하세요.

규칙:
- 3-5개 핵심 포인트를 bullet point로
- 각 포인트는 1-2문장
- 기관 동향, 주목 섹터, 핵심 전략을 반드시 포함
- 마크다운 형식

리포트:
{full_report}"""

    try:
        client = _get_client(api_key)
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        summary = response.content[0].text.strip()

        return DashboardSummaryResult(
            summary=summary,
            model_used=model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    except Exception as e:
        logger.error("Failed to condense report for dashboard: %s", e)
        return DashboardSummaryResult(
            summary="",
            model_used=model,
            input_tokens=0,
            output_tokens=0,
        )
