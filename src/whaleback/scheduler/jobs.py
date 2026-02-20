import logging
from datetime import date

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from whaleback.api.krx_client import KRXClient
from whaleback.collectors.stock_list import StockListCollector
from whaleback.collectors.ohlcv import OHLCVCollector
from whaleback.collectors.fundamentals import FundamentalsCollector
from whaleback.collectors.investor import InvestorTradingCollector
from whaleback.collectors.sector import SectorCollector
from whaleback.collectors.index import IndexCollector
from whaleback.config import Settings

logger = logging.getLogger(__name__)


def daily_collection(settings: Settings | None = None):
    """Master job: runs all collectors in sequence for today."""
    if settings is None:
        settings = Settings()

    client = KRXClient(
        delay=settings.krx_request_delay,
        max_retries=settings.krx_max_retries,
        backoff=settings.krx_retry_backoff,
    )
    target = date.today()

    results = {}

    # Collect sector mappings (reference data)
    try:
        sector_collector = SectorCollector(client)
        sector_collector.run(target)
        results["sector"] = {"status": "success", "count": "N/A"}
        logger.info("sector: collection complete")
    except Exception as e:
        results["sector"] = {"status": "failed", "error": str(e)}
        logger.error(f"Sector collection failed: {e}", exc_info=True)

    # Collect index data
    try:
        index_collector = IndexCollector(client)
        index_collector.run(target)
        results["market_index"] = {"status": "success", "count": "N/A"}
        logger.info("market_index: collection complete")
    except Exception as e:
        results["market_index"] = {"status": "failed", "error": str(e)}
        logger.error(f"Index collection failed: {e}", exc_info=True)

    collectors = [
        StockListCollector(client),
        OHLCVCollector(client),
        FundamentalsCollector(client),
        InvestorTradingCollector(client),
    ]

    for collector in collectors:
        try:
            count = collector.run(target)
            results[collector.collection_type] = {"status": "success", "count": count}
            logger.info(f"{collector.collection_type}: {count} records")
        except Exception as e:
            results[collector.collection_type] = {"status": "failed", "error": str(e)}
            logger.error(f"{collector.collection_type} failed: {e}", exc_info=True)
            # Continue with next collector

    logger.info(f"Daily collection complete: {results}")
    return results


def daily_analysis(settings: Settings | None = None):
    """Compute analysis scores after daily collection completes."""
    if settings is None:
        settings = Settings()

    from whaleback.analysis.compute import AnalysisComputer

    target = date.today()
    logger.info(f"Starting analysis computation for {target}")

    try:
        computer = AnalysisComputer()
        results = computer.run(target)
        logger.info(f"Analysis computation complete: {results}")
        return results
    except Exception as e:
        logger.error(f"Analysis computation failed: {e}", exc_info=True)
        raise


def create_scheduler(settings: Settings | None = None) -> BlockingScheduler:
    """Create and configure the APScheduler instance."""
    if settings is None:
        settings = Settings()

    scheduler = BlockingScheduler(timezone=settings.timezone)

    trigger = CronTrigger(
        hour=settings.schedule_hour,
        minute=settings.schedule_minute,
        day_of_week="mon-fri",
        timezone=settings.timezone,
    )

    scheduler.add_job(
        daily_collection,
        trigger=trigger,
        id="daily_collection",
        name="Daily KRX Data Collection",
        replace_existing=True,
        misfire_grace_time=3600,
        kwargs={"settings": settings},
    )

    # Add analysis job (runs after collection, at 19:00 KST by default)
    analysis_trigger = CronTrigger(
        hour=settings.analysis_schedule_hour,
        minute=settings.analysis_schedule_minute,
        day_of_week="mon-fri",
        timezone=settings.timezone,
    )

    scheduler.add_job(
        daily_analysis,
        trigger=analysis_trigger,
        id="daily_analysis",
        name="Daily Analysis Computation",
        replace_existing=True,
        misfire_grace_time=7200,
        kwargs={"settings": settings},
    )

    logger.info(
        f"Scheduler configured: collection at {settings.schedule_hour}:{settings.schedule_minute:02d} KST, "
        f"analysis at {settings.analysis_schedule_hour}:{settings.analysis_schedule_minute:02d} KST (Mon-Fri)"
    )

    return scheduler
