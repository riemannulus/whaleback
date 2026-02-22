"""Tests for news collector and scorer modules."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from whaleback.collectors.news import (
    strip_html,
    classify_source,
    classify_article_type,
    collect_news_for_ticker,
)


def test_strip_html():
    assert strip_html("<b>삼성전자</b> 실적") == "삼성전자 실적"
    assert strip_html("no tags") == "no tags"
    assert strip_html("<a href='x'>link</a> text") == "link text"


def test_classify_source():
    assert classify_source("https://www.hankyung.com/article/123") == "financial"
    assert classify_source("https://www.mk.co.kr/news/123") == "financial"
    assert classify_source("https://blog.naver.com/abc") == "portal"
    assert classify_source("https://news.naver.com/main") == "general"
    assert classify_source(None) == "general"
    assert classify_source("") == "general"


def test_classify_article_type():
    assert classify_article_type("삼성전자 3분기 영업이익 발표") == "earnings"
    assert classify_article_type("증권사 목표가 상향 리포트") == "analyst"
    assert classify_article_type("주요사항 공시 보고서") == "disclosure"
    assert classify_article_type("삼성전자 신제품 출시") == "general"


@pytest.mark.asyncio
async def test_collect_news_no_credentials():
    """With empty credentials, should return empty list."""
    result = await collect_news_for_ticker(
        ticker="005930",
        stock_name="삼성전자",
        naver_client_id="",
        naver_client_secret="",
        dart_api_key="",
    )
    assert result == []
