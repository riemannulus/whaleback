"""News collectors for Naver Search API and DART OpenAPI."""

import asyncio
import html as html_mod
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# HTML tag stripping pattern
HTML_TAG_RE = re.compile(r"<[^>]+>")

# Source classification by domain
FINANCIAL_DOMAINS = {
    "hankyung.com", "mk.co.kr", "edaily.co.kr", "mt.co.kr",
    "sedaily.com", "fnnews.com", "thebell.co.kr", "businesspost.co.kr",
}

# DART disclosure type weights
DART_TYPE_WEIGHTS: dict[str, tuple[str, float]] = {
    "A": ("주요사항보고", 2.0),
    "B": ("주요경영사항", 1.8),
    "C": ("발행공시", 1.5),
    "D": ("지분공시", 1.5),
    "E": ("기타공시", 1.0),
    "F": ("외부감사관련", 1.5),
    "G": ("펀드공시", 1.0),
    "H": ("자산유동화", 1.0),
    "I": ("거래소공시", 1.5),
    "J": ("공정위공시", 1.0),
}


def strip_html(text: str) -> str:
    """Remove HTML tags and decode HTML entities from text."""
    return html_mod.unescape(HTML_TAG_RE.sub("", text)).strip()


def classify_source(url: str | None) -> str:
    """Classify news source type from URL."""
    if not url:
        return "general"
    url_lower = url.lower()
    for domain in FINANCIAL_DOMAINS:
        if domain in url_lower:
            return "financial"
    if "blog" in url_lower or "cafe" in url_lower or "community" in url_lower:
        return "portal"
    return "general"


def classify_article_type(title: str, description: str = "") -> str:
    """Classify article type from title/description."""
    text = (title + " " + description).lower()
    if any(kw in text for kw in ["실적", "영업이익", "매출", "순이익", "어닝", "분기"]):
        return "earnings"
    if any(kw in text for kw in ["리포트", "목표가", "투자의견", "증권사", "애널리스트"]):
        return "analyst"
    if any(kw in text for kw in ["공시", "보고서", "감사", "신고"]):
        return "disclosure"
    return "general"


async def fetch_naver_news(
    stock_name: str,
    client_id: str,
    client_secret: str,
    display: int = 100,
    sort: str = "date",
) -> list[dict[str, Any]]:
    """Fetch news articles from Naver Search API.

    Args:
        stock_name: Korean stock name to search.
        client_id: Naver API client ID.
        client_secret: Naver API client secret.
        display: Number of results (max 100).
        sort: Sort order ('date' or 'sim').

    Returns:
        List of article dicts with standardized fields.
    """
    if not client_id or not client_secret:
        logger.debug("Naver API credentials not configured, skipping")
        return []

    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    params = {
        "query": stock_name,
        "display": min(display, 100),
        "sort": sort,
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers, params=params)

                # Retry on rate limit (429)
                if response.status_code == 429:
                    wait = 1.0 * (2 ** attempt)  # 1s, 2s, 4s exponential backoff
                    logger.debug("Naver 429 for '%s', retry in %.1fs", stock_name, wait)
                    await asyncio.sleep(wait)
                    continue

                response.raise_for_status()
                data = response.json()

            articles = []
            for item in data.get("items", []):
                title = strip_html(item.get("title", ""))
                description = strip_html(item.get("description", ""))
                source_url = item.get("originallink") or item.get("link", "")
                pub_date_str = item.get("pubDate", "")

                # Parse pub date (RFC 2822 format from Naver)
                published_at = _parse_naver_date(pub_date_str)
                if published_at is None:
                    continue

                source_type = classify_source(source_url)
                article_type = classify_article_type(title, description)

                articles.append({
                    "title": title,
                    "description": description,
                    "source_url": source_url,
                    "source_name": _extract_domain(source_url),
                    "published_at": published_at,
                    "source_type": source_type,
                    "article_type": article_type,
                    "importance_weight": 1.0,
                })

            logger.debug("Naver: fetched %d articles for '%s'", len(articles), stock_name)
            return articles

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                wait = 1.0 * (2 ** attempt)
                await asyncio.sleep(wait)
                continue
            logger.warning("Naver API error for '%s': %s", stock_name, e.response.status_code)
            return []
        except Exception as e:
            logger.warning("Naver fetch failed for '%s': %s", stock_name, e)
            return []

    logger.warning("Naver API exhausted retries for '%s'", stock_name)
    return []


async def fetch_dart_disclosures(
    api_key: str,
    stock_code: str,
    bgn_de: str,
    end_de: str,
) -> list[dict[str, Any]]:
    """Fetch disclosures from DART OpenAPI.

    Args:
        api_key: DART API key.
        stock_code: 6-digit stock ticker (used to filter from full list).
        bgn_de: Begin date (YYYYMMDD).
        end_de: End date (YYYYMMDD).

    Returns:
        List of disclosure dicts.
    """
    if not api_key:
        logger.debug("DART API key not configured, skipping")
        return []

    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        "crtfc_key": api_key,
        "bgn_de": bgn_de,
        "end_de": end_de,
        "stock_code": stock_code,
        "page_count": 100,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        if data.get("status") != "000":
            # DART returns status "013" for no data
            if data.get("status") == "013":
                return []
            logger.debug("DART API status: %s - %s", data.get("status"), data.get("message"))
            return []

        articles = []
        for item in data.get("list", []):
            report_nm = item.get("report_nm", "")
            rcept_dt = item.get("rcept_dt", "")
            pblntf_ty = item.get("pblntf_ty", "E")

            # Parse date
            try:
                published_at = datetime.strptime(rcept_dt, "%Y%m%d").replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue

            type_info = DART_TYPE_WEIGHTS.get(pblntf_ty, ("기타", 1.0))

            articles.append({
                "title": f"[공시] {report_nm}",
                "description": f"{type_info[0]} - {report_nm}",
                "source_url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item.get('rcept_no', '')}",
                "source_name": "DART",
                "published_at": published_at,
                "source_type": "financial",
                "article_type": "disclosure",
                "importance_weight": type_info[1],
                # Pre-scored: DART disclosures are administrative text, not suitable for BERT
                "sentiment_raw": 0.0,
                "sentiment_label": "neutral",
                "sentiment_confidence": 1.0,
                "scoring_method": "rule",
            })

        logger.debug("DART: fetched %d disclosures for %s", len(articles), stock_code)
        return articles

    except Exception as e:
        logger.warning("DART fetch failed for %s: %s", stock_code, e)
        return []


async def collect_news_for_ticker(
    ticker: str,
    stock_name: str,
    naver_client_id: str,
    naver_client_secret: str,
    dart_api_key: str,
    lookback_days: int = 14,
) -> list[dict[str, Any]]:
    """Collect all news for a single ticker from all sources.

    Returns combined and deduplicated articles list.
    """
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=lookback_days)

    # Fetch from both sources in parallel
    naver_task = fetch_naver_news(stock_name, naver_client_id, naver_client_secret)
    dart_task = fetch_dart_disclosures(
        dart_api_key, ticker,
        bgn_de=start_date.strftime("%Y%m%d"),
        end_de=end_date.strftime("%Y%m%d"),
    )

    naver_articles, dart_articles = await asyncio.gather(naver_task, dart_task)

    # Filter Naver articles by date range
    naver_filtered = [
        a for a in naver_articles
        if a["published_at"] >= start_date
    ]

    # Combine and add ticker
    all_articles = naver_filtered + dart_articles
    for article in all_articles:
        article["ticker"] = ticker

    # Deduplicate by source_url
    seen_urls: set[str] = set()
    unique_articles = []
    for article in all_articles:
        url = article.get("source_url", "")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        unique_articles.append(article)

    return unique_articles


def _parse_naver_date(date_str: str) -> datetime | None:
    """Parse Naver API date format (RFC 2822-like)."""
    if not date_str:
        return None
    try:
        # Naver format: "Thu, 20 Feb 2025 09:00:00 +0900"
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str)
    except Exception:
        try:
            # Fallback: try ISO format
            return datetime.fromisoformat(date_str)
        except Exception:
            return None


def _extract_domain(url: str) -> str:
    """Extract domain name from URL."""
    if not url:
        return "unknown"
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc or "unknown"
    except Exception:
        return "unknown"
