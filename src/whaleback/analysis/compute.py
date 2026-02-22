"""Analysis computation orchestrator.

Batch-computes quant, whale, and trend analysis for all active tickers
and persists results to analysis snapshot tables.
"""

import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
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
from whaleback.analysis.flow import (
    compute_retail_contrarian,
    compute_smart_dumb_divergence,
    compute_flow_momentum_shift,
)
from whaleback.analysis.technical import (
    compute_disparity,
    compute_bollinger,
    compute_macd,
)
from whaleback.analysis.risk import (
    compute_volatility,
    compute_beta,
    compute_max_drawdown,
)
from whaleback.analysis.composite import (
    compute_composite_score,
    detect_confluence,
    classify_composite_score,
)
from whaleback.analysis.simulation import run_monte_carlo
from whaleback.analysis.sector_flow import compute_sector_flows
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
    AnalysisFlowSnapshot,
    AnalysisTechnicalSnapshot,
    AnalysisRiskSnapshot,
    AnalysisCompositeSnapshot,
    AnalysisSimulationSnapshot,
    AnalysisSectorFlowSnapshot,
    AnalysisNewsSnapshot,
    NewsArticle,
)

logger = logging.getLogger(__name__)


def _run_simulation_worker(
    ticker: str,
    prices: list[float],
    config: dict,
) -> tuple[str, dict[str, Any] | None]:
    """Picklable worker for ProcessPoolExecutor.

    Args:
        ticker: Stock ticker.
        prices: List of closing prices.
        config: Dict of simulation parameters from Settings.

    Returns:
        (ticker, simulation_result_dict or None)
    """
    from whaleback.analysis.simulation import run_monte_carlo
    from whaleback.analysis.sim_models import SimModel

    models = tuple(SimModel)  # all four models

    weights = {
        SimModel.GBM.value: config.get("weight_gbm", 0.25),
        SimModel.GARCH.value: config.get("weight_garch", 0.30),
        SimModel.HESTON.value: config.get("weight_heston", 0.20),
        SimModel.MERTON.value: config.get("weight_merton", 0.25),
    }

    result = run_monte_carlo(
        prices,
        num_simulations=config.get("num_paths", 10000),
        ticker=ticker,
        models=models,
        weights=weights,
        garch_params={"p": config.get("garch_p", 1), "q": config.get("garch_q", 1)},
        heston_params={
            "kappa": config.get("heston_kappa", 2.0),
            "theta": config.get("heston_theta", 0.04),
            "xi": config.get("heston_xi", 0.3),
            "rho": config.get("heston_rho", -0.7),
        },
        merton_params={
            "lam": config.get("merton_lambda", 0.1),
            "mu_j": config.get("merton_mu_j", -0.02),
            "sigma_j": config.get("merton_sigma_j", 0.05),
        },
        max_sigma=config.get("max_sigma", 1.50),
        sentiment_adjustments=config.get("sentiment_adjustments"),
    )

    if result is None:
        return ticker, None

    return ticker, {
        "simulation_score": result["simulation_score"],
        "simulation_grade": result["simulation_grade"],
        "base_price": result["base_price"],
        "mu": result["mu"],
        "sigma": result["sigma"],
        "num_simulations": result["num_simulations"],
        "input_days_used": result["input_days_used"],
        "horizons": result["horizons"],
        "target_probs": result["target_probs"],
        "model_breakdown": result.get("model_breakdown"),
    }


class AnalysisComputer:
    """Orchestrates analysis computation for all tickers on a given date."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()

    def run(self, target_date: date) -> dict[str, int]:
        """Run all analysis computations for the target date.

        Returns dict with counts for each analysis type:
        {quant, whale, trend, flow, technical, risk, composite}
        """
        logger.info(f"Starting analysis computation for {target_date}")

        with get_session() as session:
            # Load active tickers
            tickers = self._get_active_tickers(session)
            logger.info(f"Found {len(tickers)} active tickers")

            if not tickers:
                return {
                    "quant": 0, "whale": 0, "trend": 0,
                    "flow": 0, "technical": 0, "risk": 0, "composite": 0,
                    "news_sentiment": 0,
                }

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
            flow_rows: list[dict[str, Any]] = []
            technical_rows: list[dict[str, Any]] = []
            risk_rows: list[dict[str, Any]] = []
            composite_rows: list[dict[str, Any]] = []
            # Accumulated for sector flow: {ticker: [investor rows]}
            investor_data_acc: dict[str, list[dict[str, Any]]] = {}
            trading_values_acc: dict[str, float] = {}

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

                    # --- Flow Analysis ---
                    flow_result = self._compute_flow(session, ticker, target_date)
                    if flow_result:
                        flow_rows.append({"trade_date": target_date, "ticker": ticker, **flow_result})

                    # --- Technical Analysis ---
                    technical_result = self._compute_technical(session, ticker, target_date)
                    if technical_result:
                        technical_rows.append({"trade_date": target_date, "ticker": ticker, **technical_result})

                    # --- Risk Analysis ---
                    risk_result = self._compute_risk(session, ticker, target_date, index_prices)
                    if risk_result:
                        risk_rows.append({"trade_date": target_date, "ticker": ticker, **risk_result})

                    # --- Simulation --- (moved to parallel phase below)

                    # --- Accumulate investor data for sector flow ---
                    inv_rows, avg_tv = self._load_investor_data_for_sector(
                        session, ticker, target_date
                    )
                    if inv_rows:
                        investor_data_acc[ticker] = inv_rows
                    if avg_tv is not None:
                        trading_values_acc[ticker] = avg_tv

                except Exception as e:
                    logger.warning(f"Analysis failed for {ticker}: {e}")
                    continue

            # --- Phase 2: News Sentiment (if enabled) ---
            news_snapshot_rows: list[dict[str, Any]] = []
            sentiment_lookup: dict[str, dict] = {}
            sentiment_adj_lookup: dict[str, dict] = {}
            all_news_articles: list[dict[str, Any]] = []

            if self.settings.news_sentiment_enabled:
                try:
                    (
                        news_snapshot_rows,
                        sentiment_lookup,
                        sentiment_adj_lookup,
                        all_news_articles,
                    ) = self._collect_and_score_news(tickers, target_date)
                except Exception as e:
                    logger.warning("News sentiment phase failed: %s", e)

            # --- Parallel Simulation Phase ---
            simulation_rows = self._compute_simulations_parallel(
                session, tickers, target_date, sentiment_adj_lookup
            )

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

            # --- Sector Flow Analysis (cross-ticker, aggregated by sector) ---
            # Computed before composite scoring so sector_flow_bonus can be passed in
            sector_flow_rows = []
            try:
                sf_results = compute_sector_flows(
                    sector_map=sector_map,
                    investor_data=investor_data_acc,
                    trading_values=trading_values_acc,
                    lookback_days=self.settings.whale_lookback_days,
                )
                for sf in sf_results:
                    sector_flow_rows.append({"trade_date": target_date, **sf})
            except Exception as e:
                logger.warning(f"Sector flow computation failed: {e}")

            # Build lookup dicts for composite scoring
            quant_lookup = {r["ticker"]: r for r in quant_rows}
            whale_lookup = {r["ticker"]: r for r in whale_rows}
            trend_lookup = {r["ticker"]: r for r in trend_rows}
            simulation_lookup = {r["ticker"]: r for r in simulation_rows}

            # Build sector flow bonus lookup: ticker -> bonus points
            sector_flow_bonus_lookup: dict[str, float] = {}
            for sf_row in sector_flow_rows:
                sector = sf_row.get("sector")
                signal = sf_row.get("signal")
                if signal in ("strong_accumulation", "mild_accumulation"):
                    # Find tickers in this sector
                    for t, s in sector_map.items():
                        if s == sector:
                            current_bonus = sector_flow_bonus_lookup.get(t, 0.0)
                            add = 15.0 if signal == "strong_accumulation" else 5.0
                            sector_flow_bonus_lookup[t] = min(current_bonus + add, 15.0)

            for ticker in tickers:
                try:
                    quant_d = quant_lookup.get(ticker)
                    whale_d = whale_lookup.get(ticker)
                    trend_d = trend_lookup.get(ticker)
                    sim_d = simulation_lookup.get(ticker)
                    sf_bonus = sector_flow_bonus_lookup.get(ticker, 0.0)

                    if not any([quant_d, whale_d, trend_d]):
                        continue

                    score_result = compute_composite_score(
                        quant_d, whale_d, trend_d, sim_d, sf_bonus,
                        sentiment_data=sentiment_lookup.get(ticker),
                    )
                    confluence = detect_confluence(
                        score_result.get("value_score"),
                        score_result.get("flow_score"),
                        score_result.get("momentum_score"),
                        score_result.get("forecast_score"),
                    )
                    classification = classify_composite_score(score_result.get("composite_score"))

                    composite_rows.append({
                        "trade_date": target_date,
                        "ticker": ticker,
                        "composite_score": score_result.get("composite_score"),
                        "value_score": score_result.get("value_score"),
                        "flow_score": score_result.get("flow_score"),
                        "momentum_score": score_result.get("momentum_score"),
                        "forecast_score": score_result.get("forecast_score"),
                        "sentiment_score": score_result.get("sentiment_score"),
                        "confidence": score_result.get("confidence"),
                        "axes_available": score_result.get("axes_available"),
                        "confluence_tier": confluence.get("confluence_tier"),
                        "confluence_pattern": confluence.get("confluence_pattern"),
                        "divergence_type": confluence.get("divergence_type"),
                        "divergence_label": confluence.get("divergence_label"),
                        "action_label": confluence.get("action_label"),
                        "action_description": confluence.get("action_description"),
                        "score_tier": classification.get("tier"),
                        "score_label": classification.get("label"),
                        "score_color": classification.get("color"),
                    })
                except Exception as e:
                    logger.warning(f"Composite scoring failed for {ticker}: {e}")
                    continue

            # Persist results
            quant_count = self._persist_snapshots(session, AnalysisQuantSnapshot, quant_rows)
            whale_count = self._persist_snapshots(session, AnalysisWhaleSnapshot, whale_rows)
            trend_count = self._persist_snapshots(session, AnalysisTrendSnapshot, trend_rows)
            flow_count = self._persist_snapshots(session, AnalysisFlowSnapshot, flow_rows)
            tech_count = self._persist_snapshots(session, AnalysisTechnicalSnapshot, technical_rows)
            risk_count = self._persist_snapshots(session, AnalysisRiskSnapshot, risk_rows)
            composite_count = self._persist_snapshots(session, AnalysisCompositeSnapshot, composite_rows)
            sim_count = self._persist_snapshots(session, AnalysisSimulationSnapshot, simulation_rows)
            sector_flow_count = self._persist_sector_flow_snapshots(session, sector_flow_rows)
            news_count = self._persist_snapshots(session, AnalysisNewsSnapshot, news_snapshot_rows)
            news_article_count = self._persist_news_articles(session, all_news_articles)

            logger.info(
                f"Analysis complete: quant={quant_count}, whale={whale_count}, "
                f"trend={trend_count}, flow={flow_count}, technical={tech_count}, "
                f"risk={risk_count}, composite={composite_count}, simulation={sim_count}, "
                f"sector_flow={sector_flow_count}, news={news_count} "
                f"(articles={news_article_count})"
            )
            return {
                "quant": quant_count,
                "whale": whale_count,
                "trend": trend_count,
                "flow": flow_count,
                "technical": tech_count,
                "risk": risk_count,
                "composite": composite_count,
                "simulation": sim_count,
                "sector_flow": sector_flow_count,
                "news_sentiment": news_count,
            }

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
                "private_equity_net": int(r.private_equity_net) if r.private_equity_net else None,
                "other_corp_net": int(r.other_corp_net) if r.other_corp_net else None,
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
            "institution_net_20d": whale_result["components"].get("institution_net", {}).get("net_total"),
            "foreign_net_20d": whale_result["components"].get("foreign_net", {}).get("net_total"),
            "pension_net_20d": whale_result["components"].get("pension_net", {}).get("net_total"),
            "private_equity_net_20d": whale_result["components"].get("private_equity_net", {}).get("net_total"),
            "other_corp_net_20d": whale_result["components"].get("other_corp_net", {}).get("net_total"),
            "institution_consistency": whale_result["components"].get("institution_net", {}).get("consistency"),
            "foreign_consistency": whale_result["components"].get("foreign_net", {}).get("consistency"),
            "pension_consistency": whale_result["components"].get("pension_net", {}).get("consistency"),
            "private_equity_consistency": whale_result["components"].get("private_equity_net", {}).get("consistency"),
            "other_corp_consistency": whale_result["components"].get("other_corp_net", {}).get("consistency"),
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

    def _compute_flow(
        self, session: Session, ticker: str, target_date: date
    ) -> dict[str, Any] | None:
        """Compute flow analysis (retail contrarian, smart/dumb divergence, momentum shift)."""
        lookback = 60  # Need 60 days for Z-score
        start_date = target_date - timedelta(days=lookback * 2)

        # Load investor trading data including individual_net
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
                "institution_net": int(r.institution_net) if r.institution_net else 0,
                "foreign_net": int(r.foreign_net) if r.foreign_net else 0,
                "pension_net": int(r.pension_net) if r.pension_net else 0,
                "individual_net": int(r.individual_net) if r.individual_net else 0,
            }
            for r in result.scalars().all()
        ]

        if not investor_rows:
            return None

        # Avg daily trading value for normalization
        avg_val_result = session.execute(
            select(func.avg(DailyOHLCV.trading_value)).where(
                and_(
                    DailyOHLCV.ticker == ticker,
                    DailyOHLCV.trade_date.between(start_date, target_date),
                )
            )
        ).scalar_one_or_none()
        avg_trading_value = float(avg_val_result) if avg_val_result else None

        retail = compute_retail_contrarian(investor_rows, avg_trading_value)
        divergence = compute_smart_dumb_divergence(investor_rows, avg_trading_value)
        shift = compute_flow_momentum_shift(investor_rows)

        return {
            "retail_z": retail.get("retail_z"),
            "retail_intensity": retail.get("retail_intensity"),
            "retail_consistency": retail.get("retail_consistency"),
            "retail_signal": retail.get("signal"),
            "divergence_score": divergence.get("divergence_score"),
            "smart_ratio": divergence.get("smart_ratio"),
            "dumb_ratio": divergence.get("dumb_ratio"),
            "divergence_signal": divergence.get("signal"),
            "shift_score": shift.get("shift_score"),
            "shift_signal": shift.get("overall_signal"),
        }

    def _compute_technical(
        self, session: Session, ticker: str, target_date: date
    ) -> dict[str, Any] | None:
        """Compute technical indicators (disparity, bollinger, MACD)."""
        # Need ~252 days for MACD + enough history
        start_date = target_date - timedelta(days=400)

        result = session.execute(
            select(DailyOHLCV.close)
            .where(
                and_(
                    DailyOHLCV.ticker == ticker,
                    DailyOHLCV.trade_date.between(start_date, target_date),
                )
            )
            .order_by(DailyOHLCV.trade_date)
        )
        prices = [float(r.close) for r in result.all()]

        if len(prices) < 20:
            return None

        disparity = compute_disparity(prices)
        bollinger = compute_bollinger(prices)
        macd = compute_macd(prices)

        return {
            "disparity_20d": disparity.get("disparity_20d"),
            "disparity_60d": disparity.get("disparity_60d"),
            "disparity_120d": disparity.get("disparity_120d"),
            "disparity_signal": disparity.get("signal"),
            "bb_upper": bollinger.get("upper"),
            "bb_center": bollinger.get("center"),
            "bb_lower": bollinger.get("lower"),
            "bb_bandwidth": bollinger.get("bandwidth"),
            "bb_percent_b": bollinger.get("percent_b"),
            "bb_signal": bollinger.get("signal"),
            "macd_value": macd.get("macd"),
            "macd_signal_line": macd.get("signal_line"),
            "macd_histogram": macd.get("histogram"),
            "macd_crossover": macd.get("crossover"),
        }

    def _compute_risk(
        self,
        session: Session,
        ticker: str,
        target_date: date,
        index_prices: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any] | None:
        """Compute risk metrics (volatility, beta, max drawdown)."""
        start_date = target_date - timedelta(days=400)

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

        if len(stock_data) < 20:
            return None

        prices = [p for _, p in stock_data]

        volatility = compute_volatility(prices)
        drawdown = compute_max_drawdown(prices)

        # Beta needs aligned index prices
        kospi_data = index_prices.get("1001", [])
        kospi_by_date = {d["trade_date"]: d["close"] for d in kospi_data}

        aligned_stock: list[float] = []
        aligned_index: list[float] = []
        for d, p in stock_data:
            if d in kospi_by_date:
                aligned_stock.append(p)
                aligned_index.append(kospi_by_date[d])

        beta = compute_beta(aligned_stock, aligned_index)

        return {
            "volatility_20d": volatility.get("volatility_20d"),
            "volatility_60d": volatility.get("volatility_60d"),
            "volatility_1y": volatility.get("volatility_1y"),
            "risk_level": volatility.get("risk_level"),
            "beta_60d": beta.get("beta_60d"),
            "beta_252d": beta.get("beta_252d"),
            "beta_interpretation": beta.get("interpretation"),
            "mdd_60d": drawdown.get("mdd_60d"),
            "mdd_1y": drawdown.get("mdd_1y"),
            "current_drawdown": drawdown.get("current_drawdown"),
            "recovery_label": drawdown.get("recovery_label"),
        }

    def _compute_simulations_parallel(
        self, session: Session, tickers: dict[str, str], target_date: date,
        sentiment_adj_lookup: dict[str, dict] | None = None,
    ) -> list[dict[str, Any]]:
        """Run Monte Carlo simulations for all tickers using ProcessPoolExecutor."""
        from datetime import timedelta

        start_date = target_date - timedelta(days=400)

        # Phase 1: Load all price data sequentially (DB I/O)
        ticker_prices: dict[str, list[float]] = {}
        for ticker in tickers:
            result = session.execute(
                select(DailyOHLCV.close)
                .where(
                    and_(
                        DailyOHLCV.ticker == ticker,
                        DailyOHLCV.trade_date.between(start_date, target_date),
                    )
                )
                .order_by(DailyOHLCV.trade_date)
            )
            prices = [float(r.close) for r in result.all()]
            if len(prices) >= self.settings.simulation_min_history_days:
                ticker_prices[ticker] = prices

        if not ticker_prices:
            return []

        # Build config dict (pickle-safe plain types)
        config = {
            "num_paths": self.settings.simulation_num_paths,
            "max_sigma": self.settings.simulation_max_sigma,
            "weight_gbm": self.settings.simulation_weight_gbm,
            "weight_garch": self.settings.simulation_weight_garch,
            "weight_heston": self.settings.simulation_weight_heston,
            "weight_merton": self.settings.simulation_weight_merton,
            "garch_p": self.settings.simulation_garch_p,
            "garch_q": self.settings.simulation_garch_q,
            "heston_kappa": self.settings.simulation_heston_kappa,
            "heston_theta": self.settings.simulation_heston_theta,
            "heston_xi": self.settings.simulation_heston_xi,
            "heston_rho": self.settings.simulation_heston_rho,
            "merton_lambda": self.settings.simulation_merton_lambda,
            "merton_mu_j": self.settings.simulation_merton_mu_j,
            "merton_sigma_j": self.settings.simulation_merton_sigma_j,
        }

        # Phase 2: Run simulations in parallel
        simulation_rows: list[dict[str, Any]] = []
        max_workers = min(self.settings.simulation_max_workers, len(ticker_prices))

        logger.info(
            "Running parallel simulations for %d tickers with %d workers",
            len(ticker_prices), max_workers,
        )

        sim_skipped = 0
        sim_failed = 0

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for ticker, prices in ticker_prices.items():
                ticker_config = config
                if sentiment_adj_lookup and ticker in sentiment_adj_lookup:
                    ticker_config = {**config, "sentiment_adjustments": sentiment_adj_lookup[ticker]}
                futures[executor.submit(_run_simulation_worker, ticker, prices, ticker_config)] = ticker

            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    _, sim_result = future.result()
                    if sim_result is not None:
                        simulation_rows.append({
                            "trade_date": target_date,
                            "ticker": ticker,
                            **sim_result,
                        })
                    else:
                        sim_skipped += 1
                except Exception as e:
                    sim_failed += 1
                    logger.warning("Parallel simulation failed for %s: %s", ticker, e)

        if sim_skipped or sim_failed:
            logger.warning(
                "Simulation stats: %d succeeded, %d skipped (insufficient data/all models failed), %d errored",
                len(simulation_rows), sim_skipped, sim_failed,
            )
        logger.info("Parallel simulations complete: %d results", len(simulation_rows))
        return simulation_rows

    # ------------------------------------------------------------------
    # News Sentiment Pipeline
    # ------------------------------------------------------------------

    def _collect_and_score_news(
        self,
        tickers: dict[str, str],
        target_date: date,
    ) -> tuple[
        list[dict[str, Any]],   # news_snapshot_rows
        dict[str, dict],        # sentiment_lookup for composite
        dict[str, dict],        # sentiment_adj_lookup for simulation
        list[dict[str, Any]],   # all_articles for NewsArticle persistence
    ]:
        """Collect news, score with BERT/LLM, compute sentiment per ticker.

        Returns:
            (news_snapshot_rows, sentiment_lookup, sentiment_adj_lookup, all_articles)
        """
        from whaleback.collectors.news import collect_news_for_ticker
        from whaleback.analysis.news_scorer import score_articles
        from whaleback.analysis.sentiment import (
            compute_sentiment_score,
            compute_sentiment_adjustments,
        )

        settings = self.settings

        async def _pipeline():
            # Phase 2a: Parallel news collection (async I/O with concurrency + rate limiting)
            # Naver API has per-second rate limits; use low concurrency + delay
            sem = asyncio.Semaphore(3)

            async def _collect_one(ticker: str, stock_name: str):
                async with sem:
                    result = await collect_news_for_ticker(
                        ticker=ticker,
                        stock_name=stock_name,
                        naver_client_id=settings.news_naver_client_id,
                        naver_client_secret=settings.news_naver_client_secret,
                        dart_api_key=settings.news_dart_api_key,
                        lookback_days=settings.news_lookback_days,
                    )
                    await asyncio.sleep(0.15)  # ~7 req/s sustained rate
                    return ticker, result

            tasks = [_collect_one(t, n) for t, n in tickers.items()]
            collection_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Organize by ticker
            ticker_articles: dict[str, list[dict]] = {}

            for result in collection_results:
                if isinstance(result, Exception):
                    logger.warning("News collection error: %s", result)
                    continue
                t, articles = result
                if articles:
                    ticker_articles[t] = articles

            logger.info(
                "News collected: %d tickers with articles, %d total articles",
                len(ticker_articles),
                sum(len(v) for v in ticker_articles.values()),
            )

            # Phase 2b: Score articles per ticker with BERT + LLM
            ticker_scored: dict[str, list[dict]] = {}
            for t, articles in ticker_articles.items():
                try:
                    scored = await score_articles(
                        articles,
                        confidence_threshold=settings.news_bert_confidence_threshold,
                        anthropic_api_key=settings.news_anthropic_api_key,
                    )
                    if scored:
                        ticker_scored[t] = scored
                except Exception as e:
                    logger.warning("Article scoring failed for %s: %s", t, e)

            # Build all_articles from scored results (sentiment fields guaranteed)
            all_articles_list: list[dict] = []
            for scored_articles in ticker_scored.values():
                all_articles_list.extend(scored_articles)

            logger.info("Scored articles for %d tickers", len(ticker_scored))
            return ticker_scored, all_articles_list

        # Run async pipeline from sync context
        ticker_scored, all_articles = asyncio.run(_pipeline())

        # Phase 2c: Compute per-ticker sentiment scores and adjustments (pure numpy, sync)
        news_snapshot_rows: list[dict[str, Any]] = []
        sentiment_lookup: dict[str, dict] = {}
        sentiment_adj_lookup: dict[str, dict] = {}

        for ticker in tickers:
            articles = ticker_scored.get(ticker, [])

            score = compute_sentiment_score(
                articles,
                half_life=settings.news_sentiment_half_life,
                min_articles=settings.news_min_articles,
            )

            adj = compute_sentiment_adjustments(
                score,
                alpha=settings.sentiment_alpha,
                beta=settings.sentiment_beta,
                delta=settings.sentiment_delta,
                gamma_lam=settings.sentiment_gamma_lam,
                gamma_mu=settings.sentiment_gamma_mu,
            )

            # Source breakdown for snapshot
            source_breakdown: dict[str, int] = {}
            for a in articles:
                src = a.get("source_name", "unknown")
                source_breakdown[src] = source_breakdown.get(src, 0) + 1

            # News snapshot row (skip no_data tickers to save DB space)
            if score.status != "no_data":
                news_snapshot_rows.append({
                    "trade_date": target_date,
                    "ticker": ticker,
                    "sentiment_score": round(score.sentiment_score, 2),
                    "direction": round(score.direction, 4),
                    "intensity": round(score.intensity, 3),
                    "confidence": round(score.confidence, 3),
                    "effective_score": round(score.effective_score, 4),
                    "sentiment_signal": score.signal,
                    "article_count": score.article_count,
                    "status": score.status,
                    "source_breakdown": source_breakdown or None,
                })

            # Sentiment lookup for composite (only active = enough articles + confidence)
            if score.status == "active":
                sentiment_lookup[ticker] = {
                    "sentiment_score": round(score.sentiment_score, 2),
                    "direction": round(score.direction, 4),
                    "intensity": round(score.intensity, 3),
                    "confidence": round(score.confidence, 3),
                    "effective_score": round(score.effective_score, 4),
                    "signal": score.signal,
                }

            # Sentiment adjustments for simulation (pickle-safe plain dict)
            if score.status == "active":
                sentiment_adj_lookup[ticker] = {
                    "drift_adj_daily": adj.drift_adj_daily,
                    "vol_multiplier": adj.vol_multiplier,
                    "var_multiplier": adj.var_multiplier,
                    "theta_mult": adj.theta_mult,
                    "v0_mult": adj.v0_mult,
                    "rho_adj": adj.rho_adj,
                    "lam_mult": adj.lam_mult,
                    "mu_j_adj": adj.mu_j_adj,
                    "sig_j_mult": adj.sig_j_mult,
                    "ensemble_weight_overrides": adj.ensemble_weight_overrides,
                }

        logger.info(
            "Sentiment computed: %d snapshots, %d active for simulation",
            len(news_snapshot_rows), len(sentiment_adj_lookup),
        )

        return news_snapshot_rows, sentiment_lookup, sentiment_adj_lookup, all_articles

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

    def _persist_news_articles(self, session: Session, articles: list[dict[str, Any]]) -> int:
        """Persist news articles with ON CONFLICT DO UPDATE on (ticker, source_url)."""
        if not articles:
            return 0

        from sqlalchemy.dialects.postgresql import insert as pg_insert

        BATCH_SIZE = 500
        total = 0
        model_columns = {c.key for c in NewsArticle.__table__.columns}

        for i in range(0, len(articles), BATCH_SIZE):
            batch = articles[i : i + BATCH_SIZE]
            clean_batch = []
            for row in batch:
                clean = {k: v for k, v in row.items() if k in model_columns}
                # Ensure required fields exist
                if not clean.get("ticker") or not clean.get("title"):
                    continue
                clean_batch.append(clean)

            if not clean_batch:
                continue

            update_cols = [
                k for k in clean_batch[0].keys()
                if k not in ("id", "ticker", "source_url", "collected_at")
            ]

            stmt = pg_insert(NewsArticle).values(clean_batch)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_news_ticker_url",
                set_={col: getattr(stmt.excluded, col) for col in update_cols},
            )
            session.execute(stmt)
            total += len(clean_batch)

        return total

    def _load_investor_data_for_sector(
        self, session: Session, ticker: str, target_date: date
    ) -> tuple[list[dict[str, Any]], float | None]:
        """Load investor trading data and avg trading value for sector flow aggregation."""
        lookback = self.settings.whale_lookback_days
        start_date = target_date - timedelta(days=lookback * 2)

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
        rows = [
            {
                "trade_date": r.trade_date,
                "institution_net": int(r.institution_net) if r.institution_net else None,
                "foreign_net": int(r.foreign_net) if r.foreign_net else None,
                "pension_net": int(r.pension_net) if r.pension_net else None,
                "private_equity_net": int(r.private_equity_net) if r.private_equity_net else None,
                "other_corp_net": int(r.other_corp_net) if r.other_corp_net else None,
            }
            for r in result.scalars().all()
        ]

        avg_val_result = session.execute(
            select(func.avg(DailyOHLCV.trading_value)).where(
                and_(
                    DailyOHLCV.ticker == ticker,
                    DailyOHLCV.trade_date.between(start_date, target_date),
                )
            )
        ).scalar_one_or_none()
        avg_trading_value = float(avg_val_result) if avg_val_result else None

        return rows, avg_trading_value

    def _persist_sector_flow_snapshots(self, session: Session, rows: list[dict[str, Any]]) -> int:
        """Batch upsert sector flow snapshot rows (triple PK: trade_date, sector, investor_type)."""
        if not rows:
            return 0

        from sqlalchemy.dialects.postgresql import insert as pg_insert

        BATCH_SIZE = 1000
        total = 0
        model = AnalysisSectorFlowSnapshot
        model_columns = {c.key for c in model.__table__.columns}

        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            clean_batch = [{k: v for k, v in row.items() if k in model_columns} for row in batch]
            update_cols = [
                k for k in clean_batch[0].keys()
                if k not in ("trade_date", "sector", "investor_type", "computed_at")
            ]
            stmt = pg_insert(model).values(clean_batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["trade_date", "sector", "investor_type"],
                set_={col: getattr(stmt.excluded, col) for col in update_cols},
            )
            session.execute(stmt)
            total += len(batch)

        return total
