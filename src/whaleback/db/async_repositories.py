import logging
from datetime import date
from typing import Any

from sqlalchemy import func, select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from whaleback.db.models import (
    Stock,
    DailyOHLCV,
    Fundamental,
    InvestorTrading,
    SectorMapping,
    CollectionLog,
    AnalysisQuantSnapshot,
    AnalysisWhaleSnapshot,
    AnalysisTrendSnapshot,
)

logger = logging.getLogger(__name__)

# Whitelist of allowed sort fields for quant rankings
ALLOWED_SORT_FIELDS = {"safety_margin", "fscore", "rim_value", "data_completeness", "investment_grade"}


async def get_stocks_paginated(
    session: AsyncSession,
    page: int = 1,
    size: int = 50,
    market: str | None = None,
    search: str | None = None,
    is_active: bool | None = True,
) -> tuple[list[dict[str, Any]], int]:
    """Get paginated stock list with optional filters. Returns (rows, total_count)."""
    query = select(Stock)
    count_query = select(func.count()).select_from(Stock)

    if market:
        query = query.where(Stock.market == market)
        count_query = count_query.where(Stock.market == market)
    if search:
        pattern = f"%{search}%"
        query = query.where((Stock.ticker.like(pattern)) | (Stock.name.like(pattern)))
        count_query = count_query.where((Stock.ticker.like(pattern)) | (Stock.name.like(pattern)))
    if is_active is not None:
        query = query.where(Stock.is_active == is_active)
        count_query = count_query.where(Stock.is_active == is_active)

    total = (await session.execute(count_query)).scalar() or 0
    query = query.order_by(Stock.ticker).offset((page - 1) * size).limit(size)
    result = await session.execute(query)
    stocks = result.scalars().all()

    return [_stock_to_dict(s) for s in stocks], total


async def get_stock_detail(session: AsyncSession, ticker: str) -> dict[str, Any] | None:
    """Get stock detail with latest price and fundamental data."""
    # Get stock
    result = await session.execute(select(Stock).where(Stock.ticker == ticker))
    stock = result.scalar_one_or_none()
    if not stock:
        return None

    # Latest OHLCV
    ohlcv_q = (
        select(DailyOHLCV)
        .where(DailyOHLCV.ticker == ticker)
        .order_by(desc(DailyOHLCV.trade_date))
        .limit(1)
    )
    ohlcv = (await session.execute(ohlcv_q)).scalar_one_or_none()

    # Latest fundamental
    fund_q = (
        select(Fundamental)
        .where(Fundamental.ticker == ticker)
        .order_by(desc(Fundamental.trade_date))
        .limit(1)
    )
    fund = (await session.execute(fund_q)).scalar_one_or_none()

    # Sector (graceful fallback if table doesn't exist yet)
    sector_name = None
    try:
        sector_q = select(SectorMapping).where(SectorMapping.ticker == ticker)
        sector = (await session.execute(sector_q)).scalar_one_or_none()
        sector_name = sector.sector if sector else None
    except Exception:
        await session.rollback()

    data = _stock_to_dict(stock)
    data["sector"] = sector_name
    data["latest_price"] = _ohlcv_to_dict(ohlcv) if ohlcv else None
    data["latest_fundamental"] = _fundamental_to_dict(fund) if fund else None
    return data


async def get_price_history(
    session: AsyncSession, ticker: str, start_date: date, end_date: date
) -> list[dict[str, Any]]:
    """Get OHLCV history for a ticker in date range."""
    query = (
        select(DailyOHLCV)
        .where(
            and_(DailyOHLCV.ticker == ticker, DailyOHLCV.trade_date.between(start_date, end_date))
        )
        .order_by(DailyOHLCV.trade_date)
    )
    result = await session.execute(query)
    return [_ohlcv_to_dict(r) for r in result.scalars().all()]


async def get_investor_history(
    session: AsyncSession, ticker: str, start_date: date, end_date: date
) -> list[dict[str, Any]]:
    """Get investor trading history for a ticker."""
    query = (
        select(InvestorTrading)
        .where(
            and_(
                InvestorTrading.ticker == ticker,
                InvestorTrading.trade_date.between(start_date, end_date),
            )
        )
        .order_by(InvestorTrading.trade_date)
    )
    result = await session.execute(query)
    return [_investor_to_dict(r) for r in result.scalars().all()]


async def get_latest_analysis_date(session: AsyncSession) -> date | None:
    """Get the most recent analysis date."""
    try:
        result = await session.execute(select(func.max(AnalysisQuantSnapshot.trade_date)))
        return result.scalar_one_or_none()
    except Exception:
        await session.rollback()
        logger.warning("AnalysisQuantSnapshot table not found, returning None")
        return None


async def get_quant_snapshot(
    session: AsyncSession, ticker: str, as_of_date: date | None = None
) -> dict[str, Any] | None:
    """Get quant analysis snapshot for a ticker."""
    try:
        if as_of_date is None:
            as_of_date = await get_latest_analysis_date(session)
            if as_of_date is None:
                return None

        query = select(AnalysisQuantSnapshot).where(
            and_(AnalysisQuantSnapshot.ticker == ticker, AnalysisQuantSnapshot.trade_date == as_of_date)
        )
        result = (await session.execute(query)).scalar_one_or_none()
        return _quant_to_dict(result) if result else None
    except Exception:
        await session.rollback()
        logger.warning(f"Failed to get quant snapshot for {ticker}, table may not exist")
        return None


async def get_whale_snapshot(
    session: AsyncSession, ticker: str, as_of_date: date | None = None
) -> dict[str, Any] | None:
    """Get whale analysis snapshot for a ticker."""
    try:
        if as_of_date is None:
            as_of_date = await get_latest_analysis_date(session)
            if as_of_date is None:
                return None

        query = select(AnalysisWhaleSnapshot).where(
            and_(AnalysisWhaleSnapshot.ticker == ticker, AnalysisWhaleSnapshot.trade_date == as_of_date)
        )
        result = (await session.execute(query)).scalar_one_or_none()
        return _whale_to_dict(result) if result else None
    except Exception:
        await session.rollback()
        logger.warning(f"Failed to get whale snapshot for {ticker}, table may not exist")
        return None


async def get_trend_snapshot(
    session: AsyncSession, ticker: str, as_of_date: date | None = None
) -> dict[str, Any] | None:
    """Get trend analysis snapshot for a ticker."""
    try:
        if as_of_date is None:
            as_of_date = await get_latest_analysis_date(session)
            if as_of_date is None:
                return None

        query = select(AnalysisTrendSnapshot).where(
            and_(AnalysisTrendSnapshot.ticker == ticker, AnalysisTrendSnapshot.trade_date == as_of_date)
        )
        result = (await session.execute(query)).scalar_one_or_none()
        return _trend_to_dict(result) if result else None
    except Exception:
        await session.rollback()
        logger.warning(f"Failed to get trend snapshot for {ticker}, table may not exist")
        return None


async def get_quant_rankings(
    session: AsyncSession,
    as_of_date: date | None = None,
    market: str | None = None,
    min_fscore: int | None = None,
    max_pbr: float | None = None,
    grade: str | None = None,
    sort_by: str = "safety_margin",
    page: int = 1,
    size: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    """Get ranked stocks by quant analysis."""
    try:
        if as_of_date is None:
            as_of_date = await get_latest_analysis_date(session)
            if as_of_date is None:
                return [], 0

        base = (
            select(AnalysisQuantSnapshot, Stock.name, Stock.market)
            .join(Stock, AnalysisQuantSnapshot.ticker == Stock.ticker)
            .where(AnalysisQuantSnapshot.trade_date == as_of_date)
        )
        count_base = (
            select(func.count())
            .select_from(AnalysisQuantSnapshot)
            .join(Stock, AnalysisQuantSnapshot.ticker == Stock.ticker)
            .where(AnalysisQuantSnapshot.trade_date == as_of_date)
        )

        if market:
            base = base.where(Stock.market == market)
            count_base = count_base.where(Stock.market == market)
        if min_fscore is not None:
            base = base.where(AnalysisQuantSnapshot.fscore >= min_fscore)
            count_base = count_base.where(AnalysisQuantSnapshot.fscore >= min_fscore)
        if grade:
            base = base.where(AnalysisQuantSnapshot.investment_grade == grade)
            count_base = count_base.where(AnalysisQuantSnapshot.investment_grade == grade)

        total = (await session.execute(count_base)).scalar() or 0

        # Sort with whitelist validation
        if sort_by not in ALLOWED_SORT_FIELDS:
            sort_by = "safety_margin"
        sort_col = getattr(AnalysisQuantSnapshot, sort_by)
        base = base.order_by(desc(sort_col).nulls_last()).offset((page - 1) * size).limit(size)

        result = await session.execute(base)
        rows = []
        for row in result.all():
            snapshot = row[0]
            d = _quant_to_dict(snapshot)
            d["name"] = row[1]
            d["market"] = row[2]
            rows.append(d)

        return rows, total
    except Exception:
        await session.rollback()
        logger.warning("Failed to get quant rankings, table may not exist")
        return [], 0


async def get_whale_top(
    session: AsyncSession,
    as_of_date: date | None = None,
    market: str | None = None,
    min_score: float | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    """Get top whale-accumulated stocks."""
    try:
        if as_of_date is None:
            as_of_date = await get_latest_analysis_date(session)
            if as_of_date is None:
                return [], 0

        base = (
            select(AnalysisWhaleSnapshot, Stock.name, Stock.market)
            .join(Stock, AnalysisWhaleSnapshot.ticker == Stock.ticker)
            .where(AnalysisWhaleSnapshot.trade_date == as_of_date)
        )
        count_base = (
            select(func.count())
            .select_from(AnalysisWhaleSnapshot)
            .join(Stock, AnalysisWhaleSnapshot.ticker == Stock.ticker)
            .where(AnalysisWhaleSnapshot.trade_date == as_of_date)
        )

        if market:
            base = base.where(Stock.market == market)
            count_base = count_base.where(Stock.market == market)
        if min_score is not None:
            base = base.where(AnalysisWhaleSnapshot.whale_score >= min_score)
            count_base = count_base.where(AnalysisWhaleSnapshot.whale_score >= min_score)

        total = (await session.execute(count_base)).scalar() or 0
        base = (
            base.order_by(desc(AnalysisWhaleSnapshot.whale_score)).offset((page - 1) * size).limit(size)
        )

        result = await session.execute(base)
        rows = []
        for row in result.all():
            snapshot = row[0]
            d = _whale_to_dict(snapshot)
            d["name"] = row[1]
            d["market"] = row[2]
            rows.append(d)

        return rows, total
    except Exception:
        await session.rollback()
        logger.warning("Failed to get whale top, table may not exist")
        return [], 0


async def get_sector_ranking(
    session: AsyncSession,
    as_of_date: date | None = None,
    market: str | None = None,
) -> list[dict[str, Any]]:
    """Get sector ranking by average RS percentile."""
    try:
        if as_of_date is None:
            as_of_date = await get_latest_analysis_date(session)
            if as_of_date is None:
                return []

        query = (
            select(
                AnalysisTrendSnapshot.sector,
                func.count().label("stock_count"),
                func.avg(AnalysisTrendSnapshot.rs_percentile).label("avg_rs_percentile"),
                func.avg(AnalysisTrendSnapshot.rs_vs_kospi_20d).label("avg_rs_20d"),
            )
            .where(
                and_(
                    AnalysisTrendSnapshot.trade_date == as_of_date,
                    AnalysisTrendSnapshot.sector.isnot(None),
                )
            )
            .group_by(AnalysisTrendSnapshot.sector)
            .order_by(desc("avg_rs_percentile"))
        )

        if market:
            query = query.join(Stock, AnalysisTrendSnapshot.ticker == Stock.ticker).where(
                Stock.market == market
            )

        result = await session.execute(query)
        return [
            {
                "sector": row.sector,
                "stock_count": row.stock_count,
                "avg_rs_percentile": float(row.avg_rs_percentile) if row.avg_rs_percentile else None,
                "avg_rs_20d": float(row.avg_rs_20d) if row.avg_rs_20d else None,
            }
            for row in result.all()
        ]
    except Exception:
        await session.rollback()
        logger.warning("Failed to get sector ranking, table may not exist")
        return []


async def get_collection_status(session: AsyncSession) -> list[dict[str, Any]]:
    """Get latest collection status per type."""
    # Subquery: max id per collection_type
    subq = (
        select(func.max(CollectionLog.id).label("max_id"))
        .group_by(CollectionLog.collection_type)
        .subquery()
    )
    query = select(CollectionLog).where(CollectionLog.id.in_(select(subq.c.max_id)))
    result = await session.execute(query)
    return [
        {
            "collection_type": log.collection_type,
            "target_date": log.target_date.isoformat(),
            "status": log.status,
            "records_count": log.records_count,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            "error_message": log.error_message,
        }
        for log in result.scalars().all()
    ]


# --- Helper functions for dict conversion ---


def _stock_to_dict(s: Stock) -> dict[str, Any]:
    return {
        "ticker": s.ticker,
        "name": s.name,
        "market": s.market,
        "is_active": s.is_active,
        "listed_date": s.listed_date.isoformat() if s.listed_date else None,
        "delisted_date": s.delisted_date.isoformat() if s.delisted_date else None,
    }


def _ohlcv_to_dict(o: DailyOHLCV) -> dict[str, Any]:
    return {
        "trade_date": o.trade_date.isoformat(),
        "open": int(o.open) if o.open else None,
        "high": int(o.high) if o.high else None,
        "low": int(o.low) if o.low else None,
        "close": int(o.close),
        "volume": int(o.volume),
        "trading_value": int(o.trading_value) if o.trading_value else None,
        "change_rate": float(o.change_rate) if o.change_rate else None,
    }


def _fundamental_to_dict(f: Fundamental) -> dict[str, Any]:
    return {
        "trade_date": f.trade_date.isoformat(),
        "bps": float(f.bps) if f.bps else None,
        "per": float(f.per) if f.per else None,
        "pbr": float(f.pbr) if f.pbr else None,
        "eps": float(f.eps) if f.eps else None,
        "div": float(f.div) if f.div else None,
        "dps": float(f.dps) if f.dps else None,
        "roe": float(f.roe) if f.roe else None,
    }


def _investor_to_dict(i: InvestorTrading) -> dict[str, Any]:
    return {
        "trade_date": i.trade_date.isoformat(),
        "institution_net": int(i.institution_net) if i.institution_net else None,
        "foreign_net": int(i.foreign_net) if i.foreign_net else None,
        "individual_net": int(i.individual_net) if i.individual_net else None,
        "pension_net": int(i.pension_net) if i.pension_net else None,
    }


def _quant_to_dict(q: AnalysisQuantSnapshot) -> dict[str, Any]:
    return {
        "ticker": q.ticker,
        "trade_date": q.trade_date.isoformat(),
        "rim_value": float(q.rim_value) if q.rim_value else None,
        "safety_margin": float(q.safety_margin) if q.safety_margin else None,
        "fscore": q.fscore,
        "fscore_detail": q.fscore_detail,
        "investment_grade": q.investment_grade,
        "data_completeness": float(q.data_completeness) if q.data_completeness else None,
    }


def _whale_to_dict(w: AnalysisWhaleSnapshot) -> dict[str, Any]:
    return {
        "ticker": w.ticker,
        "trade_date": w.trade_date.isoformat(),
        "whale_score": float(w.whale_score) if w.whale_score else None,
        "institution_net_20d": int(w.institution_net_20d) if w.institution_net_20d else None,
        "foreign_net_20d": int(w.foreign_net_20d) if w.foreign_net_20d else None,
        "pension_net_20d": int(w.pension_net_20d) if w.pension_net_20d else None,
        "institution_consistency": float(w.institution_consistency)
        if w.institution_consistency
        else None,
        "foreign_consistency": float(w.foreign_consistency) if w.foreign_consistency else None,
        "pension_consistency": float(w.pension_consistency) if w.pension_consistency else None,
        "signal": w.signal,
    }


def _trend_to_dict(t: AnalysisTrendSnapshot) -> dict[str, Any]:
    return {
        "ticker": t.ticker,
        "trade_date": t.trade_date.isoformat(),
        "rs_vs_kospi_20d": float(t.rs_vs_kospi_20d) if t.rs_vs_kospi_20d else None,
        "rs_vs_kospi_60d": float(t.rs_vs_kospi_60d) if t.rs_vs_kospi_60d else None,
        "rs_percentile": t.rs_percentile,
        "sector": t.sector,
    }
