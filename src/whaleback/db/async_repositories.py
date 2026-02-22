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
    AnalysisFlowSnapshot,
    AnalysisTechnicalSnapshot,
    AnalysisRiskSnapshot,
    AnalysisCompositeSnapshot,
    AnalysisSimulationSnapshot,
    AnalysisSectorFlowSnapshot,
)

logger = logging.getLogger(__name__)

# Whitelist of allowed sort fields for quant rankings
ALLOWED_SORT_FIELDS = {"safety_margin", "fscore", "rim_value", "data_completeness", "investment_grade"}

# Whitelist of allowed sort fields for composite rankings
ALLOWED_COMPOSITE_SORT_FIELDS = {"composite_score", "value_score", "flow_score", "momentum_score", "confluence_tier"}

# Whitelist of allowed sort fields for simulation rankings
ALLOWED_SIMULATION_SORT_FIELDS = {"simulation_score"}


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
            as_of_date = await get_latest_trend_date(session)
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
    signal: str | None = None,
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
        if signal:
            base = base.where(AnalysisWhaleSnapshot.signal == signal)
            count_base = count_base.where(AnalysisWhaleSnapshot.signal == signal)

        total = (await session.execute(count_base)).scalar() or 0
        base = (
            base.order_by(desc(AnalysisWhaleSnapshot.whale_score).nulls_last()).offset((page - 1) * size).limit(size)
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


async def get_latest_trend_date(session: AsyncSession) -> date | None:
    """Get the most recent trend analysis date (independent of quant)."""
    try:
        result = await session.execute(select(func.max(AnalysisTrendSnapshot.trade_date)))
        return result.scalar_one_or_none()
    except Exception:
        await session.rollback()
        logger.warning("AnalysisTrendSnapshot table not found, returning None")
        return None


async def get_sector_ranking(
    session: AsyncSession,
    as_of_date: date | None = None,
    market: str | None = None,
) -> list[dict[str, Any]]:
    """Get sector ranking by average RS percentile."""
    try:
        if as_of_date is None:
            as_of_date = await get_latest_trend_date(session)
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


async def get_composite_snapshot(
    session: AsyncSession, ticker: str, as_of_date: date | None = None
) -> dict[str, Any] | None:
    """Get composite analysis snapshot for a ticker."""
    try:
        if as_of_date is None:
            as_of_date = await get_latest_analysis_date(session)
            if as_of_date is None:
                return None

        query = select(AnalysisCompositeSnapshot).where(
            and_(AnalysisCompositeSnapshot.ticker == ticker, AnalysisCompositeSnapshot.trade_date == as_of_date)
        )
        result = (await session.execute(query)).scalar_one_or_none()
        return _composite_to_dict(result) if result else None
    except Exception:
        await session.rollback()
        logger.warning(f"Failed to get composite snapshot for {ticker}, table may not exist")
        return None


async def get_flow_snapshot(
    session: AsyncSession, ticker: str, as_of_date: date | None = None
) -> dict[str, Any] | None:
    """Get flow analysis snapshot for a ticker."""
    try:
        if as_of_date is None:
            as_of_date = await get_latest_analysis_date(session)
            if as_of_date is None:
                return None

        query = select(AnalysisFlowSnapshot).where(
            and_(AnalysisFlowSnapshot.ticker == ticker, AnalysisFlowSnapshot.trade_date == as_of_date)
        )
        result = (await session.execute(query)).scalar_one_or_none()
        return _flow_to_dict(result) if result else None
    except Exception:
        await session.rollback()
        logger.warning(f"Failed to get flow snapshot for {ticker}, table may not exist")
        return None


async def get_technical_snapshot(
    session: AsyncSession, ticker: str, as_of_date: date | None = None
) -> dict[str, Any] | None:
    """Get technical analysis snapshot for a ticker."""
    try:
        if as_of_date is None:
            as_of_date = await get_latest_analysis_date(session)
            if as_of_date is None:
                return None

        query = select(AnalysisTechnicalSnapshot).where(
            and_(AnalysisTechnicalSnapshot.ticker == ticker, AnalysisTechnicalSnapshot.trade_date == as_of_date)
        )
        result = (await session.execute(query)).scalar_one_or_none()
        return _technical_to_dict(result) if result else None
    except Exception:
        await session.rollback()
        logger.warning(f"Failed to get technical snapshot for {ticker}, table may not exist")
        return None


async def get_risk_snapshot(
    session: AsyncSession, ticker: str, as_of_date: date | None = None
) -> dict[str, Any] | None:
    """Get risk analysis snapshot for a ticker."""
    try:
        if as_of_date is None:
            as_of_date = await get_latest_analysis_date(session)
            if as_of_date is None:
                return None

        query = select(AnalysisRiskSnapshot).where(
            and_(AnalysisRiskSnapshot.ticker == ticker, AnalysisRiskSnapshot.trade_date == as_of_date)
        )
        result = (await session.execute(query)).scalar_one_or_none()
        return _risk_to_dict(result) if result else None
    except Exception:
        await session.rollback()
        logger.warning(f"Failed to get risk snapshot for {ticker}, table may not exist")
        return None


async def get_composite_rankings(
    session: AsyncSession,
    as_of_date: date | None = None,
    market: str | None = None,
    min_score: float | None = None,
    min_confluence: int | None = None,
    score_tier: str | None = None,
    sort_by: str = "composite_score",
    page: int = 1,
    size: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    """Get ranked stocks by WCS composite score."""
    try:
        if as_of_date is None:
            as_of_date = await get_latest_analysis_date(session)
            if as_of_date is None:
                return [], 0

        base = (
            select(AnalysisCompositeSnapshot, Stock.name, Stock.market)
            .join(Stock, AnalysisCompositeSnapshot.ticker == Stock.ticker)
            .where(AnalysisCompositeSnapshot.trade_date == as_of_date)
        )
        count_base = (
            select(func.count())
            .select_from(AnalysisCompositeSnapshot)
            .join(Stock, AnalysisCompositeSnapshot.ticker == Stock.ticker)
            .where(AnalysisCompositeSnapshot.trade_date == as_of_date)
        )

        if market:
            base = base.where(Stock.market == market)
            count_base = count_base.where(Stock.market == market)
        if min_score is not None:
            base = base.where(AnalysisCompositeSnapshot.composite_score >= min_score)
            count_base = count_base.where(AnalysisCompositeSnapshot.composite_score >= min_score)
        if min_confluence is not None:
            base = base.where(AnalysisCompositeSnapshot.confluence_tier >= min_confluence)
            count_base = count_base.where(AnalysisCompositeSnapshot.confluence_tier >= min_confluence)
        if score_tier:
            base = base.where(AnalysisCompositeSnapshot.score_tier == score_tier)
            count_base = count_base.where(AnalysisCompositeSnapshot.score_tier == score_tier)

        total = (await session.execute(count_base)).scalar() or 0

        if sort_by not in ALLOWED_COMPOSITE_SORT_FIELDS:
            sort_by = "composite_score"
        sort_col = getattr(AnalysisCompositeSnapshot, sort_by)
        base = base.order_by(desc(sort_col).nulls_last()).offset((page - 1) * size).limit(size)

        result = await session.execute(base)
        rows = []
        for row in result.all():
            snapshot = row[0]
            d = _composite_to_dict(snapshot)
            d["name"] = row[1]
            d["market"] = row[2]
            rows.append(d)

        return rows, total
    except Exception:
        await session.rollback()
        logger.warning("Failed to get composite rankings, table may not exist")
        return [], 0


async def get_simulation_snapshot(
    session: AsyncSession, ticker: str, as_of_date: date | None = None
) -> dict[str, Any] | None:
    """Get simulation snapshot for a ticker."""
    try:
        if as_of_date is None:
            as_of_date = await get_latest_analysis_date(session)
            if as_of_date is None:
                return None
        query = select(AnalysisSimulationSnapshot).where(
            and_(AnalysisSimulationSnapshot.ticker == ticker, AnalysisSimulationSnapshot.trade_date == as_of_date)
        )
        result = (await session.execute(query)).scalar_one_or_none()
        return _simulation_to_dict(result) if result else None
    except Exception:
        await session.rollback()
        logger.warning(f"Failed to get simulation snapshot for {ticker}")
        return None


async def get_simulation_top(
    session: AsyncSession,
    as_of_date: date | None = None,
    market: str | None = None,
    min_score: float | None = None,
    sort_by: str = "simulation_score",
    page: int = 1,
    size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    """Get top stocks by simulation score."""
    try:
        if as_of_date is None:
            as_of_date = await get_latest_analysis_date(session)
            if as_of_date is None:
                return [], 0
        base = (
            select(AnalysisSimulationSnapshot, Stock.name, Stock.market)
            .join(Stock, AnalysisSimulationSnapshot.ticker == Stock.ticker)
            .where(AnalysisSimulationSnapshot.trade_date == as_of_date)
            .where(AnalysisSimulationSnapshot.simulation_score.isnot(None))
        )
        count_base = (
            select(func.count())
            .select_from(AnalysisSimulationSnapshot)
            .join(Stock, AnalysisSimulationSnapshot.ticker == Stock.ticker)
            .where(AnalysisSimulationSnapshot.trade_date == as_of_date)
            .where(AnalysisSimulationSnapshot.simulation_score.isnot(None))
        )
        if market:
            base = base.where(Stock.market == market)
            count_base = count_base.where(Stock.market == market)
        if min_score is not None:
            base = base.where(AnalysisSimulationSnapshot.simulation_score >= min_score)
            count_base = count_base.where(AnalysisSimulationSnapshot.simulation_score >= min_score)
        total = (await session.execute(count_base)).scalar() or 0
        base = base.order_by(desc(AnalysisSimulationSnapshot.simulation_score).nulls_last()).offset((page - 1) * size).limit(size)
        result = await session.execute(base)
        rows = []
        for row in result.all():
            snapshot = row[0]
            d = _simulation_to_dict(snapshot)
            d["name"] = row[1]
            d["market"] = row[2]
            rows.append(d)
        return rows, total
    except Exception:
        await session.rollback()
        logger.warning("Failed to get simulation top")
        return [], 0


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
        "financial_invest_net": int(i.financial_invest_net) if i.financial_invest_net else None,
        "insurance_net": int(i.insurance_net) if i.insurance_net else None,
        "trust_net": int(i.trust_net) if i.trust_net else None,
        "private_equity_net": int(i.private_equity_net) if i.private_equity_net else None,
        "bank_net": int(i.bank_net) if i.bank_net else None,
        "other_financial_net": int(i.other_financial_net) if i.other_financial_net else None,
        "other_corp_net": int(i.other_corp_net) if i.other_corp_net else None,
        "other_foreign_net": int(i.other_foreign_net) if i.other_foreign_net else None,
        "total_net": int(i.total_net) if i.total_net else None,
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
        "private_equity_net_20d": int(w.private_equity_net_20d) if w.private_equity_net_20d else None,
        "other_corp_net_20d": int(w.other_corp_net_20d) if w.other_corp_net_20d else None,
        "institution_consistency": float(w.institution_consistency) if w.institution_consistency else None,
        "foreign_consistency": float(w.foreign_consistency) if w.foreign_consistency else None,
        "pension_consistency": float(w.pension_consistency) if w.pension_consistency else None,
        "private_equity_consistency": float(w.private_equity_consistency) if w.private_equity_consistency else None,
        "other_corp_consistency": float(w.other_corp_consistency) if w.other_corp_consistency else None,
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


def _flow_to_dict(f: AnalysisFlowSnapshot) -> dict[str, Any]:
    return {
        "ticker": f.ticker,
        "trade_date": f.trade_date.isoformat(),
        "retail_z": float(f.retail_z) if f.retail_z is not None else None,
        "retail_intensity": float(f.retail_intensity) if f.retail_intensity is not None else None,
        "retail_consistency": float(f.retail_consistency) if f.retail_consistency is not None else None,
        "retail_signal": f.retail_signal,
        "divergence_score": float(f.divergence_score) if f.divergence_score is not None else None,
        "smart_ratio": float(f.smart_ratio) if f.smart_ratio is not None else None,
        "dumb_ratio": float(f.dumb_ratio) if f.dumb_ratio is not None else None,
        "divergence_signal": f.divergence_signal,
        "shift_score": float(f.shift_score) if f.shift_score is not None else None,
        "shift_signal": f.shift_signal,
    }


def _technical_to_dict(t: AnalysisTechnicalSnapshot) -> dict[str, Any]:
    return {
        "ticker": t.ticker,
        "trade_date": t.trade_date.isoformat(),
        "disparity_20d": float(t.disparity_20d) if t.disparity_20d is not None else None,
        "disparity_60d": float(t.disparity_60d) if t.disparity_60d is not None else None,
        "disparity_120d": float(t.disparity_120d) if t.disparity_120d is not None else None,
        "disparity_signal": t.disparity_signal,
        "bb_upper": float(t.bb_upper) if t.bb_upper is not None else None,
        "bb_center": float(t.bb_center) if t.bb_center is not None else None,
        "bb_lower": float(t.bb_lower) if t.bb_lower is not None else None,
        "bb_bandwidth": float(t.bb_bandwidth) if t.bb_bandwidth is not None else None,
        "bb_percent_b": float(t.bb_percent_b) if t.bb_percent_b is not None else None,
        "bb_signal": t.bb_signal,
        "macd_value": float(t.macd_value) if t.macd_value is not None else None,
        "macd_signal_line": float(t.macd_signal_line) if t.macd_signal_line is not None else None,
        "macd_histogram": float(t.macd_histogram) if t.macd_histogram is not None else None,
        "macd_crossover": t.macd_crossover,
    }


def _risk_to_dict(r: AnalysisRiskSnapshot) -> dict[str, Any]:
    return {
        "ticker": r.ticker,
        "trade_date": r.trade_date.isoformat(),
        "volatility_20d": float(r.volatility_20d) if r.volatility_20d is not None else None,
        "volatility_60d": float(r.volatility_60d) if r.volatility_60d is not None else None,
        "volatility_1y": float(r.volatility_1y) if r.volatility_1y is not None else None,
        "risk_level": r.risk_level,
        "beta_60d": float(r.beta_60d) if r.beta_60d is not None else None,
        "beta_252d": float(r.beta_252d) if r.beta_252d is not None else None,
        "beta_interpretation": r.beta_interpretation,
        "mdd_60d": float(r.mdd_60d) if r.mdd_60d is not None else None,
        "mdd_1y": float(r.mdd_1y) if r.mdd_1y is not None else None,
        "current_drawdown": float(r.current_drawdown) if r.current_drawdown is not None else None,
        "recovery_label": r.recovery_label,
    }


def _simulation_to_dict(s: AnalysisSimulationSnapshot) -> dict[str, Any]:
    horizons = s.horizons or {}
    horizon_6m = horizons.get("126", {}) or {}
    horizon_3m = horizons.get("63", {}) or {}
    expected_return_pct_6m = horizon_6m.get("expected_return_pct")
    upside_prob_3m = horizon_3m.get("upside_prob")
    return {
        "ticker": s.ticker,
        "trade_date": s.trade_date.isoformat(),
        "simulation_score": float(s.simulation_score) if s.simulation_score is not None else None,
        "simulation_grade": s.simulation_grade,
        "base_price": int(s.base_price) if s.base_price else None,
        "mu": float(s.mu) if s.mu is not None else None,
        "sigma": float(s.sigma) if s.sigma is not None else None,
        "num_simulations": s.num_simulations,
        "input_days_used": s.input_days_used,
        "horizons": s.horizons,
        "target_probs": s.target_probs,
        "expected_return_pct_6m": float(expected_return_pct_6m) if expected_return_pct_6m is not None else None,
        "upside_prob_3m": float(upside_prob_3m) if upside_prob_3m is not None else None,
        "model_breakdown": s.model_breakdown,
    }


def _composite_to_dict(c: AnalysisCompositeSnapshot) -> dict[str, Any]:
    return {
        "ticker": c.ticker,
        "trade_date": c.trade_date.isoformat(),
        "composite_score": float(c.composite_score) if c.composite_score is not None else None,
        "value_score": float(c.value_score) if c.value_score is not None else None,
        "flow_score": float(c.flow_score) if c.flow_score is not None else None,
        "momentum_score": float(c.momentum_score) if c.momentum_score is not None else None,
        "forecast_score": float(c.forecast_score) if c.forecast_score is not None else None,
        "confidence": float(c.confidence) if c.confidence is not None else None,
        "axes_available": c.axes_available,
        "confluence_tier": c.confluence_tier,
        "confluence_pattern": c.confluence_pattern,
        "divergence_type": c.divergence_type,
        "divergence_label": c.divergence_label,
        "action_label": c.action_label,
        "action_description": c.action_description,
        "score_tier": c.score_tier,
        "score_label": c.score_label,
        "score_color": c.score_color,
    }


async def get_sector_flow_overview(
    session: AsyncSession, as_of_date: date | None = None
) -> list[dict[str, Any]]:
    """Get sector flow overview grouped by sector."""
    try:
        if as_of_date is None:
            as_of_date = await get_latest_analysis_date(session)
            if as_of_date is None:
                return []
        query = (
            select(AnalysisSectorFlowSnapshot)
            .where(AnalysisSectorFlowSnapshot.trade_date == as_of_date)
            .order_by(AnalysisSectorFlowSnapshot.sector)
        )
        result = await session.execute(query)
        rows = result.scalars().all()

        # Group by sector
        sector_data: dict[str, dict[str, Any]] = {}
        for row in rows:
            if row.sector not in sector_data:
                sector_data[row.sector] = {"sector": row.sector, "flows": {}, "stock_count": row.stock_count or 0}
            sector_data[row.sector]["flows"][row.investor_type] = {
                "net_purchase": int(row.net_purchase) if row.net_purchase else None,
                "intensity": float(row.intensity) if row.intensity is not None else None,
                "consistency": float(row.consistency) if row.consistency is not None else None,
                "signal": row.signal,
                "trend_5d": int(row.trend_5d) if row.trend_5d else None,
                "trend_20d": int(row.trend_20d) if row.trend_20d else None,
            }

        # Compute dominant_signal: the signal that appears most among flows for each sector
        for sector_entry in sector_data.values():
            signal_counts: dict[str, int] = {}
            for flow in sector_entry["flows"].values():
                sig = flow.get("signal")
                if sig:
                    signal_counts[sig] = signal_counts.get(sig, 0) + 1
            sector_entry["dominant_signal"] = max(signal_counts, key=signal_counts.__getitem__) if signal_counts else None

        return list(sector_data.values())
    except Exception:
        await session.rollback()
        logger.warning("Failed to get sector flow overview")
        return []


async def get_sector_flow_heatmap(
    session: AsyncSession, as_of_date: date | None = None, metric: str = "intensity"
) -> dict[str, Any]:
    """Get heatmap data for sector flow visualization."""
    try:
        if as_of_date is None:
            as_of_date = await get_latest_analysis_date(session)
            if as_of_date is None:
                return {"sectors": [], "investor_types": [], "values": [], "signals": []}
        query = (
            select(AnalysisSectorFlowSnapshot)
            .where(AnalysisSectorFlowSnapshot.trade_date == as_of_date)
            .order_by(AnalysisSectorFlowSnapshot.sector)
        )
        result = await session.execute(query)
        rows = result.scalars().all()

        sectors_set: dict[str, int] = {}
        types_set: dict[str, int] = {}
        data_map: dict[tuple[str, str], tuple[float | None, str | None]] = {}

        for row in rows:
            if row.sector not in sectors_set:
                sectors_set[row.sector] = len(sectors_set)
            if row.investor_type not in types_set:
                types_set[row.investor_type] = len(types_set)

            val = None
            if metric == "intensity":
                val = float(row.intensity) if row.intensity is not None else None
            elif metric == "consistency":
                val = float(row.consistency) if row.consistency is not None else None
            elif metric == "net_purchase":
                val = float(row.net_purchase) if row.net_purchase is not None else None

            data_map[(row.sector, row.investor_type)] = (val, row.signal)

        sectors = list(sectors_set.keys())
        investor_types = list(types_set.keys())
        values = []
        signals = []
        for sector in sectors:
            row_vals = []
            row_sigs = []
            for inv_type in investor_types:
                v, s = data_map.get((sector, inv_type), (None, None))
                row_vals.append(v)
                row_sigs.append(s)
            values.append(row_vals)
            signals.append(row_sigs)

        return {"sectors": sectors, "investor_types": investor_types, "matrix": values, "signals": signals}
    except Exception:
        await session.rollback()
        logger.warning("Failed to get sector flow heatmap")
        return {"sectors": [], "investor_types": [], "matrix": [], "signals": []}
