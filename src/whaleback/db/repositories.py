import logging
from datetime import date
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from whaleback.db.engine import get_session
from whaleback.db.models import DailyOHLCV, Fundamental, InvestorTrading, Stock

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000


def upsert_stocks(stocks: list[dict[str, Any]], session: Session | None = None) -> int:
    """Upsert stock master records."""
    if not stocks:
        return 0

    def _do(sess: Session):
        stmt = pg_insert(Stock).values(stocks)
        stmt = stmt.on_conflict_do_update(
            index_elements=["ticker"],
            set_={
                "name": stmt.excluded.name,
                "market": stmt.excluded.market,
                "is_active": stmt.excluded.is_active,
                "delisted_date": stmt.excluded.delisted_date,
            },
        )
        sess.execute(stmt)

    if session is not None:
        _do(session)
    else:
        with get_session() as sess:
            _do(sess)
    return len(stocks)


def upsert_ohlcv(rows: list[dict[str, Any]], session: Session | None = None) -> int:
    """Upsert daily OHLCV records in batches."""
    return _batch_upsert(
        DailyOHLCV,
        rows,
        conflict_columns=["trade_date", "ticker"],
        update_columns=["open", "high", "low", "close", "volume", "trading_value", "change_rate"],
        session=session,
    )


def upsert_fundamentals(rows: list[dict[str, Any]], session: Session | None = None) -> int:
    """Upsert fundamental records in batches."""
    return _batch_upsert(
        Fundamental,
        rows,
        conflict_columns=["trade_date", "ticker"],
        update_columns=["bps", "per", "pbr", "eps", "div", "dps", "roe"],
        session=session,
    )


def upsert_investor_trading(rows: list[dict[str, Any]], session: Session | None = None) -> int:
    """Upsert investor trading records in batches."""
    return _batch_upsert(
        InvestorTrading,
        rows,
        conflict_columns=["trade_date", "ticker"],
        update_columns=[
            "institution_net",
            "foreign_net",
            "individual_net",
            "pension_net",
            "financial_invest_net",
            "insurance_net",
            "trust_net",
            "private_equity_net",
            "bank_net",
            "other_financial_net",
            "other_corp_net",
            "other_foreign_net",
            "total_net",
        ],
        session=session,
    )


def upsert_sector_mapping(rows: list[dict[str, Any]], session: Session | None = None) -> int:
    """Upsert sector mapping records."""
    from whaleback.db.models import SectorMapping

    if not rows:
        return 0

    def _do(sess: Session):
        stmt = pg_insert(SectorMapping).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["ticker"],
            set_={
                "sector": stmt.excluded.sector,
                "sector_en": stmt.excluded.sector_en,
                "sub_sector": stmt.excluded.sub_sector,
            },
        )
        sess.execute(stmt)

    if session is not None:
        _do(session)
    else:
        with get_session() as sess:
            _do(sess)
    logger.info(f"Upserted {len(rows)} sector mappings")
    return len(rows)


def upsert_market_index(rows: list[dict[str, Any]], session: Session | None = None) -> int:
    """Upsert market index records in batches."""
    from whaleback.db.models import MarketIndex

    return _batch_upsert(
        MarketIndex,
        rows,
        conflict_columns=["trade_date", "index_code"],
        update_columns=["index_name", "close", "change_rate", "volume", "trading_value"],
        session=session,
    )


def _batch_upsert(
    model,
    rows: list[dict[str, Any]],
    conflict_columns: list[str],
    update_columns: list[str],
    session: Session | None = None,
) -> int:
    """Generic batch upsert using PostgreSQL ON CONFLICT DO UPDATE."""
    if not rows:
        return 0

    def _do(sess: Session):
        total = 0
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            stmt = pg_insert(model).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=conflict_columns,
                set_={col: getattr(stmt.excluded, col) for col in update_columns},
            )
            sess.execute(stmt)
            total += len(batch)
        return total

    if session is not None:
        result = _do(session)
    else:
        with get_session() as sess:
            result = _do(sess)

    logger.info(f"Upserted {result} rows into {model.__tablename__}")
    return result


def get_active_tickers(session: Session) -> dict[str, Stock]:
    """Get all currently active stocks as a dict keyed by ticker."""
    stocks = session.query(Stock).filter(Stock.is_active.is_(True)).all()
    return {s.ticker: s for s in stocks}


def is_collected(collection_type: str, target_date: date) -> bool:
    """Check if a collection run already succeeded for the given type and date."""
    from whaleback.db.models import CollectionLog

    with get_session() as session:
        log = (
            session.query(CollectionLog)
            .filter_by(
                collection_type=collection_type,
                target_date=target_date,
                status="success",
            )
            .first()
        )
        return log is not None
