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

_SECTION_KEY_MAP: dict[str, str] = {
    "핵심 요약": "executive_summary",
    "시장 환경": "market_environment",
    "기관/외국인 수급 분석": "institutional_flow",
    "섹터 로테이션 및 테마 분석": "sector_rotation",
    "종목 스포트라이트": "stock_spotlight",
    "퀀트 시그널 리뷰": "quant_signal",
    "추세/모멘텀 분석": "trend_momentum",
    "뉴스 감성 영향 분석": "news_sentiment",
    "리스크 평가": "risk_assessment",
    "이전 리포트 비교 및 정확도": "previous_comparison",
    "전략적 제언": "strategy",
    "관심 종목 리스트": "watchlist",
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

    # Build key_insights: summary per section
    key_insights: dict[str, Any] = {}
    _STOCK_LIST_KEYS = {"stock_spotlight", "watchlist"}
    for key, content in sections.items():
        if key in _STOCK_LIST_KEYS:
            # Extract stock names/tickers from bullet points (bold **name** preferred)
            stocks = []
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith(("-", "*", "•")):
                    clean = re.sub(r"^[-*•]\s*", "", line)
                    bold_match = re.search(r"\*\*(.+?)\*\*", clean)
                    if bold_match:
                        stocks.append(bold_match.group(1))
                    elif clean:
                        stocks.append(clean.split(":")[0].split("(")[0].strip()[:30])
            key_insights[key] = stocks[:10]
        else:
            # Take first 2-3 non-empty lines as summary (500 char cap for richer context)
            lines = [l.strip() for l in content.split("\n") if l.strip() and not l.strip().startswith("#")]
            summary_lines = []
            for l in lines:
                clean = re.sub(r"^[-*•]\s*", "", l)
                if clean:
                    summary_lines.append(clean)
                if len(summary_lines) >= 3:
                    break
            key_insights[key] = " ".join(summary_lines)[:500] if summary_lines else ""

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

SYSTEM_PROMPT = """당신은 20년 경력의 시니어 퀀트 애널리스트이자 기관투자 전략가입니다.
한국 주식시장(KOSPI/KOSDAQ)에 대한 일일 투자 리포트를 작성합니다.

## 역할과 전문성
- 증권사 리서치센터 수준의 전문 투자 리포트 작성
- 기관투자자와 개인투자자 모두에게 가치 있는 인사이트 제공
- 데이터 기반의 객관적 분석과 명확한 액션 아이템 제시
- 한국 시장 특수성(기관/외국인/연기금 수급, 섹터 로테이션 패턴) 깊은 이해

## 작성 원칙
1. **데이터 중심**: 모든 주장은 제공된 데이터의 구체적 수치로 뒷받침
2. **비교 분석**: 이전 리포트가 있으면 반드시 변화와 연속성을 분석
3. **실행 가능성**: 추상적 전망이 아닌 구체적 행동 지침 제시
4. **리스크 균형**: 낙관론과 비관론을 균형있게 제시하되 리스크를 과소평가하지 않음
5. **전문 용어**: 표준 금융/투자 용어 사용, 단 핵심 개념은 간결하게 설명

## 리포트 구조 (12개 섹션, 반드시 이 순서와 제목 사용)

각 섹션은 `## 섹션제목` 형식의 마크다운 헤더로 시작합니다.

### ## 핵심 요약
- 오늘 시장의 가장 중요한 3-5개 포인트를 불릿으로 제시
- 투자자가 30초 안에 시장 상황을 파악할 수 있도록 작성
- 각 포인트는 구체적 수치를 포함

### ## 시장 환경
- 전체 시장 현황 (분석 종목 수, 평균 점수 등)
- 시장 전반의 분위기와 방향성 진단
- 거시적 맥락에서의 현재 위치 해석

### ## 기관/외국인 수급 분석
- 기관, 외국인, 연기금 등 주요 투자 주체별 순매수/순매도 분석
- 수급 데이터에서 드러나는 기관의 전략적 의도 해석
- 주목할 만한 수급 이상 징후나 패턴 변화
- 고래 점수(whale_score) 상위 종목의 의미 분석

### ## 섹터 로테이션 및 테마 분석
- 섹터별 자금 흐름 분석 (어디서 빠지고 어디로 유입되는지)
- 투자 주체별 섹터 선호도 차이 분석
- 신규 테마 또는 기존 테마의 강화/약화 판단
- 섹터 간 상대강도 비교

### ## 종목 스포트라이트
- 종합점수(composite_score) 상위/하위 종목 심층 분석
- 왜 이 종목들이 주목받고 있는지 다차원 분석 (퀀트+수급+추세+뉴스)
- 각 종목의 투자 매력도와 리스크 요인을 균형있게 제시
- **종목명** 형식으로 볼드 처리

### ## 퀀트 시그널 리뷰
- 퀀트 점수 분포와 전체적인 시그널 강도 평가
- 퀀트 점수와 다른 지표(수급, 추세) 간의 일치/괴리 분석
- 퀀트 모델이 포착한 주목할 패턴

### ## 추세/모멘텀 분석
- 추세 점수 분포와 시장 전체 모멘텀 진단
- 추세 전환 신호가 보이는 종목/섹터 식별
- 이동평균선 정배열/역배열 종목 현황
- 모멘텀 강화/약화 패턴 분석

### ## 뉴스 감성 영향 분석
- 뉴스 감성 분석 결과 요약 (긍정/부정 비율)
- 뉴스 감성이 실제 수급/주가에 미치는 영향 분석
- 감성과 실제 시장 반응의 괴리가 있는 종목 식별
- 주목할 뉴스 이벤트와 예상 영향

### ## 리스크 평가
- 현재 시장의 주요 리스크 요인 3-5개 제시
- 각 리스크의 발생 가능성과 영향도 평가
- 리스크 완화 또는 헤지 전략 제안
- 시장 급변 시나리오 분석

### ## 이전 리포트 비교 및 정확도
- 이전 리포트의 주요 전망과 실제 결과 비교
- 맞은 예측과 빗나간 예측 구분 및 원인 분석
- 연속되는 트렌드와 새로운 변화 식별
- 분석 프레임워크의 개선점 도출
(이전 리포트가 없으면 "첫 리포트로, 향후 비교 기준점이 됩니다." 로 간략히 작성)

### ## 전략적 제언
- 단기(1-3일), 중기(1-2주) 관점의 투자 전략 제시
- 포지션 구축/청산/유지 권장 사항
- 시장 상황별 대응 시나리오 (상승/횡보/하락)
- 핵심 전략을 한 문장으로 요약

### ## 관심 종목 리스트
- 매수 관심: 종합 분석 결과 매수 매력이 높은 3-5개 종목
- 관찰 필요: 추가 확인이 필요한 3-5개 종목
- 주의 필요: 리스크가 높아 주의가 필요한 3-5개 종목
- 각 종목에 대해 한 줄 근거 제시

## 출력 형식
- 마크다운 형식 사용 (## 헤더, **볼드**, - 불릿)
- 모든 섹션은 반드시 ## 으로 시작
- 표(table)는 사용하지 않음 (파싱 호환성)
- 수치는 소수점 1자리까지 표시
- 금액은 억원 단위 사용"""


def _build_user_prompt(data: MarketSummaryInput, previous_report: str | None = None) -> str:
    """Build the user prompt with all data sections."""
    parts: list[str] = []
    parts.append(f"# 시장 분석 데이터 ({data.trade_date})\n")

    # 1. Market stats
    if data.market_stats:
        ms = data.market_stats
        parts.append("## [시장 기본 통계]")
        parts.append(f"- 분석 대상: {ms.get('total_tickers', 'N/A')}개 종목")
        avg_composite = ms.get("avg_composite", None)
        avg_whale = ms.get("avg_whale", None)
        avg_trend = ms.get("avg_trend", None)
        parts.append(f"- 평균 종합점수: {avg_composite:.1f}" if isinstance(avg_composite, (int, float)) else f"- 평균 종합점수: {avg_composite}")
        parts.append(f"- 평균 고래점수: {avg_whale:.1f}" if isinstance(avg_whale, (int, float)) else f"- 평균 고래점수: {avg_whale}")
        parts.append(f"- 평균 추세점수: {avg_trend:.1f}" if isinstance(avg_trend, (int, float)) else f"- 평균 추세점수: {avg_trend}")
        parts.append("")

    # 2. Sector flows (cap at 80)
    if data.sector_flows:
        parts.append("## [섹터별 수급 현황]")
        for sf in data.sector_flows[:80]:
            parts.append(
                f"- {sf.get('sector_name', '?')} | {sf.get('investor_type', '?')} | "
                f"순매수: {sf.get('net_purchase', 0):.1f}억 | "
                f"매수: {sf.get('buy_amount', 0):.1f}억 | "
                f"매도: {sf.get('sell_amount', 0):.1f}억"
            )
        parts.append("")

    # 3. Whale top (cap at 25)
    if data.whale_top:
        parts.append("## [고래 매집 상위 종목 (수급 강도)]")
        for w in data.whale_top[:25]:
            comps = w.get("components", {})
            comp_str = " | ".join(
                f"{k}: 순매수{v.get('net_purchase', 0):.0f}억, 매수{v.get('buy_days', 0)}일/매도{v.get('sell_days', 0)}일, 추세:{v.get('trend', '?')}"
                for k, v in comps.items()
                if isinstance(v, dict)
            )
            parts.append(
                f"- {w.get('name', '?')}({w.get('ticker', '?')}) | "
                f"고래점수: {w.get('whale_score', 0):.1f} | {comp_str}"
            )
        parts.append("")

    # 4. Trend data (cap at 40)
    if data.trend_data:
        parts.append("## [추세/모멘텀 분석 데이터]")
        for t in data.trend_data[:40]:
            parts.append(
                f"- {t.get('name', '?')}({t.get('ticker', '?')}) | "
                f"추세점수: {t.get('trend_score', 0):.1f} | "
                f"방향: {t.get('trend_direction', '?')} | "
                f"모멘텀: {t.get('momentum', 0):.2f} | "
                f"MA정배열: {t.get('ma_alignment', 'N/A')}"
            )
        parts.append("")

    # 5. News data (cap at 30)
    if data.news_data:
        parts.append("## [뉴스 감성 분석 데이터]")
        if isinstance(data.news_data, list):
            for n in data.news_data[:30]:
                parts.append(
                    f"- {n.get('name', '?')}({n.get('ticker', '?')}) | "
                    f"기사수: {n.get('article_count', 0)} | "
                    f"평균감성: {n.get('avg_sentiment', 0):.3f} | "
                    f"긍정: {n.get('positive_count', 0)} | "
                    f"부정: {n.get('negative_count', 0)}"
                )
        else:
            parts.append(json.dumps(data.news_data, ensure_ascii=False, default=str))
        parts.append("")

    # 6. Composite top (cap at 25)
    if data.composite_top:
        parts.append("## [종합점수 상위 종목]")
        for c in data.composite_top[:25]:
            parts.append(
                f"- {c.get('name', '?')}({c.get('ticker', '?')}) | "
                f"종합: {c.get('composite_score', 0):.1f} | "
                f"퀀트: {c.get('quant_score', 0):.1f} | "
                f"수급: {c.get('whale_score', 0):.1f} | "
                f"추세: {c.get('trend_score', 0):.1f} | "
                f"시뮬레이션 중앙수익률: {c.get('simulation_median_return', 0):.2f}%"
            )
        parts.append("")

    # 7. Composite bottom (cap at 25)
    if data.composite_bottom:
        parts.append("## [종합점수 하위 종목]")
        for c in data.composite_bottom[:25]:
            parts.append(
                f"- {c.get('name', '?')}({c.get('ticker', '?')}) | "
                f"종합: {c.get('composite_score', 0):.1f} | "
                f"퀀트: {c.get('quant_score', 0):.1f} | "
                f"수급: {c.get('whale_score', 0):.1f} | "
                f"추세: {c.get('trend_score', 0):.1f} | "
                f"시뮬레이션 중앙수익률: {c.get('simulation_median_return', 0):.2f}%"
            )
        parts.append("")

    # 8. Flow data - divergence (cap at 25)
    if data.flow_data:
        parts.append("## [수급 상세 데이터 (투자자별)]")
        for f in data.flow_data[:25]:
            parts.append(
                f"- {f.get('name', '?')}({f.get('ticker', '?')}) | "
                f"{f.get('investor_type', '?')} | "
                f"순매수: {f.get('net_purchase', 0):.1f}억 | "
                f"매수: {f.get('buy_amount', 0):.1f}억 | "
                f"매도: {f.get('sell_amount', 0):.1f}억"
            )
        parts.append("")

    # 9. Previous report for comparison
    if previous_report:
        parts.append("## [이전 리포트 (비교 참고용)]")
        parts.append(previous_report[:4000])
        parts.append("")
    else:
        parts.append("## [이전 리포트]")
        parts.append("이전 리포트 없음 (첫 리포트)")
        parts.append("")

    parts.append(
        "위 데이터를 기반으로 12개 섹션의 전문 투자 리포트를 작성해 주세요. "
        "반드시 지정된 섹션 순서와 ## 헤더 형식을 따라주세요."
    )

    return "\n".join(parts)


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
    model = "claude-opus-4-6"

    # Build sector highlights from raw data (no LLM needed)
    sector_highlights = _build_sector_highlights(data.sector_flows)

    try:
        client = _get_client(api_key)
        user_prompt = _build_user_prompt(data, previous_report)

        with client.messages.stream(
            model=model,
            max_tokens=32768,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            full_report = stream.get_final_text().strip()
            final_message = stream.get_final_message()

        key_insights = _parse_report_sections(full_report)

        return MarketReportResult(
            full_report=full_report,
            key_insights=key_insights,
            sector_highlights=sector_highlights,
            model_used=model,
            input_tokens=final_message.usage.input_tokens,
            output_tokens=final_message.usage.output_tokens,
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

    condense_system = (
        "당신은 전문 투자 리포트 요약가입니다. 긴 분석 리포트를 투자자가 30초 안에 파악할 수 있는 "
        "핵심 불릿 포인트 5-7개로 압축합니다. 각 포인트는 구체적 수치를 포함하고, "
        "가장 중요한 변화와 액션 아이템을 강조합니다. 한국어로 작성하세요."
    )

    prompt = (
        "다음 투자 리포트를 5-7개의 핵심 불릿 포인트로 요약해 주세요.\n"
        "각 포인트는 '- ' 로 시작하고, 구체적 수치를 포함해야 합니다.\n"
        "가장 중요한 시장 변화, 수급 동향, 전략적 시사점을 우선 배치하세요.\n\n"
        f"{full_report}"
    )

    try:
        client = _get_client(api_key)
        response = client.messages.create(
            model=model,
            max_tokens=1500,
            system=condense_system,
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
