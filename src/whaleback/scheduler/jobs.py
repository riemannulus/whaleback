import logging
from datetime import date

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from whaleback.api.krx_client import KRXClient
from whaleback.collectors.stock_list import StockListCollector
from whaleback.collectors.ohlcv import OHLCVCollector
from whaleback.collectors.fundamentals import FundamentalsCollector
from whaleback.collectors.investor import InvestorTradingCollector
from whaleback.config import Settings
from whaleback.logging_config import setup_logging

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

    collectors = [
        StockListCollector(client),
        OHLCVCollector(client),
        FundamentalsCollector(client),
        InvestorTradingCollector(client),
    ]

    results = {}
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

    logger.info(
        f"Scheduler configured: daily at {settings.schedule_hour}:{settings.schedule_minute:02d} "
        f"KST (Mon-Fri)"
    )

    return scheduler
