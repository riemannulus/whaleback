"""Analysis computation orchestrator.

Batch-computes quant, whale, and trend analysis for all active tickers
and persists results to analysis snapshot tables.
"""

import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import Session

from whaleback.analysis.quant import (
    compute_rim,
    compute_safety_margin,
    compute_fscore,
    compute_investment_grade,
)
from whaleback.analysis.whale import compute_whale_score
from whaleback.analysis.trend import compute_relative_strength, compute_rs_percentile
from whaleback.config import Settings
from whaleback.db.engine import get_session
from whaleback.db.models import (
    Stock,
    DailyOHLCV,
    Fundamental,
    InvestorTrading,
    SectorMapping,
    MarketIndex,
    AnalysisQuantSnapshot,
    AnalysisWhaleSnapshot,
    AnalysisTrendSnapshot,
)

logger = logging.getLogger(__name__)


class AnalysisComputer:
    """Orchestrates analysis computation for all tickers on a given date."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()

    def run(self, target_date: date) -> dict[str, int]:
        """Run all analysis computations for the target date.

        Returns dict with counts: {quant: N, whale: N, trend: N}
        """
        logger.info(f"Starting analysis computation for {target_date}")

        with get_session() as session:
            # Load active tickers
            tickers = self._get_active_tickers(session)
            logger.info(f"Found {len(tickers)} active tickers")

            if not tickers:
                return {"quant": 0, "whale": 0, "trend": 0}

            # Pre-compute sector medians for F-Score
            sector_medians = self._compute_sector_medians(session, target_date)
            logger.info(f"Computed sector medians for {len(sector_medians)} sectors")

            # Load sector mappings
            sector_map = self._load_sector_map(session)

            # Load index prices for RS calculation (last 60 trading days)
            index_prices = self._load_index_prices(session, target_date, days=60)

            # Compute per ticker
            quant_rows: list[dict[str, Any]] = []
            whale_rows: list[dict[str, Any]] = []
            trend_rows: list[dict[str, Any]] = []

            for i, (ticker, stock_name) in enumerate(tickers.items()):
                if (i + 1) % 200 == 0:
                    logger.info(f"Processing {i + 1}/{len(tickers)}...")

                try:
                    # --- Quant Analysis ---
                    quant_result = self._compute_quant(
                        session, ticker, target_date, sector_map, sector_medians
                    )
                    if quant_result:
                        quant_rows.append(
                            {
                                "trade_date": target_date,
                                "ticker": ticker,
                                **quant_result,
                            }
                        )

                    # --- Whale Analysis ---
                    whale_result = self._compute_whale(session, ticker, target_date)
                    if whale_result:
                        whale_rows.append(
                            {
                                "trade_date": target_date,
                                "ticker": ticker,
                                **whale_result,
                            }
                        )

                    # --- Trend Analysis ---
                    trend_result = self._compute_trend(
                        session, ticker, target_date, index_prices, sector_map
                    )
                    if trend_result:
                        trend_rows.append(
                            {
                                "trade_date": target_date,
                                "ticker": ticker,
                                **trend_result,
                            }
                        )

                except Exception as e:
                    logger.warning(f"Analysis failed for {ticker}: {e}")
                    continue

            # Compute RS percentiles (needs all RS values first)
            if trend_rows:
                all_rs_20d = [
                    r.get("rs_vs_kospi_20d")
                    for r in trend_rows
                    if r.get("rs_vs_kospi_20d") is not None
                ]
                for row in trend_rows:
                    rs = row.get("rs_vs_kospi_20d")
                    row["rs_percentile"] = compute_rs_percentile(rs, all_rs_20d)

            # Persist results
            quant_count = self._persist_snapshots(session, AnalysisQuantSnapshot, quant_rows)
            whale_count = self._persist_snapshots(session, AnalysisWhaleSnapshot, whale_rows)
            trend_count = self._persist_snapshots(session, AnalysisTrendSnapshot, trend_rows)

            logger.info(
                f"Analysis complete: quant={quant_count}, whale={whale_count}, trend={trend_count}"
            )
            return {"quant": quant_count, "whale": whale_count, "trend": trend_count}

    # ------------------------------------------------------------------
    # Data loading helpers
    # ------------------------------------------------------------------

    def _get_active_tickers(self, session: Session) -> dict[str, str]:
        """Get all active tickers as {ticker: name}."""
        result = session.execute(select(Stock.ticker, Stock.name).where(Stock.is_active.is_(True)))
        return {row.ticker: row.name for row in result.all()}

    def _load_sector_map(self, session: Session) -> dict[str, str]:
        """Load ticker -> sector mapping."""
        result = session.execute(select(SectorMapping.ticker, SectorMapping.sector))
        return {row.ticker: row.sector for row in result.all()}

    def _compute_sector_medians(
        self, session: Session, target_date: date
    ) -> dict[str, dict[str, float]]:
        """Pre-compute median PBR and PER per sector for F-Score signals."""
        query = (
            select(SectorMapping.sector, Fundamental.pbr, Fundamental.per)
            .join(
                Fundamental,
                and_(
                    SectorMapping.ticker == Fundamental.ticker,
                    Fundamental.trade_date == target_date,
                ),
            )
            .where(Fundamental.pbr.isnot(None))
        )
        result = session.execute(query)

        sector_data: dict[str, dict[str, list[float]]] = {}
        for row in result.all():
            if row.sector not in sector_data:
                sector_data[row.sector] = {"pbr": [], "per": []}
            if row.pbr and float(row.pbr) > 0:
                sector_data[row.sector]["pbr"].append(float(row.pbr))
            if row.per and float(row.per) > 0:
                sector_data[row.sector]["per"].append(float(row.per))

        medians: dict[str, dict[str, float]] = {}
        for sector, data in sector_data.items():
            medians[sector] = {}
            if data["pbr"]:
                sorted_pbr = sorted(data["pbr"])
                mid = len(sorted_pbr) // 2
                medians[sector]["median_pbr"] = sorted_pbr[mid]
            if data["per"]:
                sorted_per = sorted(data["per"])
                mid = len(sorted_per) // 2
                medians[sector]["median_per"] = sorted_per[mid]

        return medians

    def _load_index_prices(
        self, session: Session, target_date: date, days: int = 60
    ) -> dict[str, list[dict[str, Any]]]:
        """Load index price history for RS computation."""
        start_date = target_date - timedelta(days=days * 2)  # Extra buffer for non-trading days

        result = session.execute(
            select(MarketIndex)
            .where(
                and_(
                    MarketIndex.trade_date.between(start_date, target_date),
                    MarketIndex.index_code.in_(["1001", "2001"]),
                )
            )
            .order_by(MarketIndex.trade_date)
        )

        prices: dict[str, list[dict[str, Any]]] = {"1001": [], "2001": []}
        for row in result.scalars().all():
            prices.setdefault(row.index_code, []).append(
                {
                    "trade_date": row.trade_date,
                    "close": float(row.close),
                }
            )

        return prices

    # ------------------------------------------------------------------
    # Per-ticker analysis computations
    # ------------------------------------------------------------------

    def _compute_quant(
        self,
        session: Session,
        ticker: str,
        target_date: date,
        sector_map: dict[str, str],
        sector_medians: dict[str, dict[str, float]],
    ) -> dict[str, Any] | None:
        """Compute quant analysis for a single ticker."""
        # Current fundamentals
        current_fund = session.execute(
            select(Fundamental).where(
                and_(
                    Fundamental.ticker == ticker,
                    Fundamental.trade_date == target_date,
                )
            )
        ).scalar_one_or_none()

        if not current_fund:
            return None

        current = {
            "bps": float(current_fund.bps) if current_fund.bps else None,
            "per": float(current_fund.per) if current_fund.per else None,
            "pbr": float(current_fund.pbr) if current_fund.pbr else None,
            "eps": float(current_fund.eps) if current_fund.eps else None,
            "div": float(current_fund.div) if current_fund.div else None,
            "dps": float(current_fund.dps) if current_fund.dps else None,
            "roe": float(current_fund.roe) if current_fund.roe else None,
        }

        # Previous year fundamentals (approximate: ~365 days back)
        prev_date = target_date - timedelta(days=365)
        prev_fund = session.execute(
            select(Fundamental)
            .where(and_(Fundamental.ticker == ticker, Fundamental.trade_date <= prev_date))
            .order_by(desc(Fundamental.trade_date))
            .limit(1)
        ).scalar_one_or_none()

        previous = None
        if prev_fund:
            previous = {
                "bps": float(prev_fund.bps) if prev_fund.bps else None,
                "per": float(prev_fund.per) if prev_fund.per else None,
                "pbr": float(prev_fund.pbr) if prev_fund.pbr else None,
                "eps": float(prev_fund.eps) if prev_fund.eps else None,
                "div": float(prev_fund.div) if prev_fund.div else None,
                "roe": float(prev_fund.roe) if prev_fund.roe else None,
            }

        # Volume data (last ~40 trading days)
        vol_result = session.execute(
            select(DailyOHLCV.volume, DailyOHLCV.trade_date)
            .where(and_(DailyOHLCV.ticker == ticker, DailyOHLCV.trade_date <= target_date))
            .order_by(desc(DailyOHLCV.trade_date))
            .limit(40)
        )
        vol_rows = vol_result.all()
        volume_current = int(vol_rows[0].volume) if vol_rows else None
        volume_previous = int(vol_rows[-1].volume) if len(vol_rows) > 20 else None

        # Current price
        price_row = session.execute(
            select(DailyOHLCV.close).where(
                and_(DailyOHLCV.ticker == ticker, DailyOHLCV.trade_date == target_date)
            )
        ).scalar_one_or_none()
        current_price = int(price_row) if price_row else None

        # Sector medians
        sector = sector_map.get(ticker)
        s_medians = sector_medians.get(sector) if sector else None

        # Compute RIM
        rim_result = compute_rim(
            bps=current.get("bps"),
            roe=current.get("roe"),
            risk_free_rate=self.settings.risk_free_rate,
            equity_risk_premium=self.settings.equity_risk_premium,
        )

        rim_value = rim_result.get("rim_value")

        # Compute safety margin
        margin_result = compute_safety_margin(rim_value, current_price)
        safety_margin = margin_result.get("safety_margin_pct")

        # Compute F-Score
        fscore_result = compute_fscore(
            current, previous, s_medians, volume_current, volume_previous
        )
        fscore = fscore_result["total_score"]
        data_completeness = fscore_result["data_completeness"]

        # Compute grade
        grade_result = compute_investment_grade(fscore, safety_margin, data_completeness)

        return {
            "rim_value": rim_value,
            "safety_margin": safety_margin,
            "fscore": fscore,
            "fscore_detail": fscore_result["criteria"],
            "investment_grade": grade_result["grade"],
            "data_completeness": data_completeness,
        }

    def _compute_whale(
        self, session: Session, ticker: str, target_date: date
    ) -> dict[str, Any] | None:
        """Compute whale analysis for a single ticker."""
        lookback = self.settings.whale_lookback_days
        start_date = target_date - timedelta(days=lookback * 2)

        # Load investor trading data
        result = session.execute(
            select(InvestorTrading)
            .where(
                and_(
                    InvestorTrading.ticker == ticker,
                    InvestorTrading.trade_date.between(start_date, target_date),
                )
            )
            .order_by(InvestorTrading.trade_date)
        )
        investor_rows = [
            {
                "trade_date": r.trade_date,
                "institution_net": int(r.institution_net) if r.institution_net else None,
                "foreign_net": int(r.foreign_net) if r.foreign_net else None,
                "pension_net": int(r.pension_net) if r.pension_net else None,
            }
            for r in result.scalars().all()
        ]

        if not investor_rows:
            return None

        # Average daily trading value for intensity calculation
        avg_val_result = session.execute(
            select(func.avg(DailyOHLCV.trading_value)).where(
                and_(
                    DailyOHLCV.ticker == ticker,
                    DailyOHLCV.trade_date.between(start_date, target_date),
                )
            )
        ).scalar_one_or_none()
        avg_trading_value = float(avg_val_result) if avg_val_result else None

        whale_result = compute_whale_score(investor_rows, avg_trading_value, lookback)

        return {
            "whale_score": whale_result["whale_score"],
            "institution_net_20d": whale_result["components"]
            .get("institution_net", {})
            .get("net_total"),
            "foreign_net_20d": whale_result["components"].get("foreign_net", {}).get("net_total"),
            "pension_net_20d": whale_result["components"].get("pension_net", {}).get("net_total"),
            "institution_consistency": whale_result["components"]
            .get("institution_net", {})
            .get("consistency"),
            "foreign_consistency": whale_result["components"]
            .get("foreign_net", {})
            .get("consistency"),
            "pension_consistency": whale_result["components"]
            .get("pension_net", {})
            .get("consistency"),
            "signal": whale_result["signal"],
        }

    def _compute_trend(
        self,
        session: Session,
        ticker: str,
        target_date: date,
        index_prices: dict[str, list[dict[str, Any]]],
        sector_map: dict[str, str],
    ) -> dict[str, Any] | None:
        """Compute trend analysis for a single ticker."""
        # Load stock prices (last ~60 trading days, with buffer)
        start_date = target_date - timedelta(days=120)
        result = session.execute(
            select(DailyOHLCV.trade_date, DailyOHLCV.close)
            .where(
                and_(
                    DailyOHLCV.ticker == ticker,
                    DailyOHLCV.trade_date.between(start_date, target_date),
                )
            )
            .order_by(DailyOHLCV.trade_date)
        )
        stock_data = [(r.trade_date, float(r.close)) for r in result.all()]

        if len(stock_data) < 5:
            return None

        # Get KOSPI index prices matching stock dates
        kospi_data = index_prices.get("1001", [])
        kospi_by_date = {d["trade_date"]: d["close"] for d in kospi_data}

        # Align prices by date
        aligned_stock: list[float] = []
        aligned_index: list[float] = []
        for d, p in stock_data:
            if d in kospi_by_date:
                aligned_stock.append(p)
                aligned_index.append(kospi_by_date[d])

        rs_20d = None
        rs_60d = None

        if len(aligned_stock) >= 20:
            rs_20d_result = compute_relative_strength(aligned_stock[-20:], aligned_index[-20:])
            rs_20d = rs_20d_result.get("current_rs")

        if len(aligned_stock) >= 60:
            rs_60d_result = compute_relative_strength(aligned_stock[-60:], aligned_index[-60:])
            rs_60d = rs_60d_result.get("current_rs")

        sector = sector_map.get(ticker)

        return {
            "rs_vs_kospi_20d": round(rs_20d, 4) if rs_20d else None,
            "rs_vs_kospi_60d": round(rs_60d, 4) if rs_60d else None,
            "rs_percentile": None,  # Computed after all tickers processed
            "sector": sector,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist_snapshots(self, session: Session, model: type, rows: list[dict[str, Any]]) -> int:
        """Batch upsert analysis snapshot rows."""
        if not rows:
            return 0

        from sqlalchemy.dialects.postgresql import insert as pg_insert

        BATCH_SIZE = 1000
        total = 0

        # Get column names from model (for filtering row keys)
        model_columns = {c.key for c in model.__table__.columns}

        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            # Filter to only model columns (exclude any extra keys)
            clean_batch = [{k: v for k, v in row.items() if k in model_columns} for row in batch]

            update_cols = [
                k for k in clean_batch[0].keys() if k not in ("trade_date", "ticker", "computed_at")
            ]

            stmt = pg_insert(model).values(clean_batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["trade_date", "ticker"],
                set_={col: getattr(stmt.excluded, col) for col in update_cols},
            )
            session.execute(stmt)
            total += len(batch)

        return total
