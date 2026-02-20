import logging
import sys
from datetime import date, datetime, timedelta

import click

from whaleback.config import Settings
from whaleback.logging_config import setup_logging

logger = logging.getLogger(__name__)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(verbose: bool):
    """Whaleback - Korean Stock Market Data Pipeline"""
    setup_logging()
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)


@cli.command()
@click.option("--date", "-d", "target_date", type=str, default=None,
              help="Target date in YYYYMMDD format (default: today)")
def run_once(target_date: str | None):
    """Run a single collection cycle."""
    from whaleback.scheduler.jobs import daily_collection

    settings = Settings()

    if target_date:
        # Override date.today() by running collectors individually
        from whaleback.api.krx_client import KRXClient
        from whaleback.collectors.stock_list import StockListCollector
        from whaleback.collectors.ohlcv import OHLCVCollector
        from whaleback.collectors.fundamentals import FundamentalsCollector
        from whaleback.collectors.investor import InvestorTradingCollector

        target = datetime.strptime(target_date, "%Y%m%d").date()
        client = KRXClient(
            delay=settings.krx_request_delay,
            max_retries=settings.krx_max_retries,
            backoff=settings.krx_retry_backoff,
        )
        collectors = [
            StockListCollector(client),
            OHLCVCollector(client),
            FundamentalsCollector(client),
            InvestorTradingCollector(client),
        ]
        for collector in collectors:
            try:
                count = collector.run(target)
                click.echo(f"  {collector.collection_type}: {count} records")
            except Exception as e:
                click.echo(f"  {collector.collection_type}: FAILED - {e}", err=True)
    else:
        results = daily_collection(settings)
        for ctype, result in results.items():
            if result["status"] == "success":
                click.echo(f"  {ctype}: {result['count']} records")
            else:
                click.echo(f"  {ctype}: FAILED - {result.get('error', 'unknown')}", err=True)

    click.echo("Collection complete.")


@cli.command()
def schedule():
    """Start the scheduler (runs daily at configured time)."""
    from whaleback.scheduler.jobs import create_scheduler

    settings = Settings()
    click.echo(
        f"Starting scheduler: daily at {settings.schedule_hour}:{settings.schedule_minute:02d} "
        f"KST (Mon-Fri)"
    )
    click.echo("Press Ctrl+C to stop.")

    scheduler = create_scheduler(settings)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        click.echo("\nScheduler stopped.")
        scheduler.shutdown()


@cli.command()
@click.option("--start", "-s", "start_date", required=True,
              help="Start date in YYYYMMDD format")
@click.option("--end", "-e", "end_date", default=None,
              help="End date in YYYYMMDD format (default: yesterday)")
@click.option("--type", "-t", "collection_types", multiple=True,
              type=click.Choice(["stock_sync", "ohlcv", "fundamentals", "investor"]),
              default=("stock_sync", "ohlcv", "fundamentals", "investor"),
              help="Collection types to backfill")
@click.option("--skip-existing", is_flag=True, default=True,
              help="Skip dates that already have successful collections")
def backfill(start_date: str, end_date: str | None, collection_types: tuple[str, ...],
             skip_existing: bool):
    """Backfill historical data for a date range."""
    from whaleback.api.krx_client import KRXClient
    from whaleback.collectors.stock_list import StockListCollector
    from whaleback.collectors.ohlcv import OHLCVCollector
    from whaleback.collectors.fundamentals import FundamentalsCollector
    from whaleback.collectors.investor import InvestorTradingCollector
    from whaleback.db.repositories import is_collected

    settings = Settings()
    client = KRXClient(
        delay=settings.krx_request_delay,
        max_retries=5,
        backoff=3.0,
    )

    collector_map = {
        "stock_sync": StockListCollector,
        "ohlcv": OHLCVCollector,
        "fundamentals": FundamentalsCollector,
        "investor": InvestorTradingCollector,
    }

    start = datetime.strptime(start_date, "%Y%m%d").date()
    end = datetime.strptime(end_date, "%Y%m%d").date() if end_date else date.today() - timedelta(days=1)

    click.echo(f"Backfilling {', '.join(collection_types)} from {start} to {end}")

    current = start
    total_days = 0
    while current <= end:
        # Skip weekends (Mon=0, Sun=6)
        if current.weekday() >= 5:
            current += timedelta(days=1)
            continue

        total_days += 1
        click.echo(f"\n[{current}]")

        for ctype in collection_types:
            if skip_existing and is_collected(ctype, current):
                click.echo(f"  {ctype}: skipped (already collected)")
                continue

            collector = collector_map[ctype](client)
            try:
                count = collector.run(current)
                click.echo(f"  {ctype}: {count} records")
            except Exception as e:
                click.echo(f"  {ctype}: FAILED - {e}", err=True)

        current += timedelta(days=1)

    click.echo(f"\nBackfill complete. Processed {total_days} trading days.")


@cli.command("init-db")
def init_db():
    """Initialize database tables and partitions."""
    from sqlalchemy import text

    from whaleback.db.engine import get_engine
    from whaleback.db.models import Base

    engine = get_engine()

    click.echo("Creating tables...")
    Base.metadata.create_all(engine)

    # Create yearly partitions for partitioned tables
    click.echo("Creating partitions...")
    partition_tables = {
        "daily_ohlcv": "daily_ohlcv",
        "fundamentals": "fundamentals",
        "investor_trading": "investor_trading",
    }

    with engine.begin() as conn:
        for table_name in partition_tables.values():
            for year in range(2020, date.today().year + 3):
                partition_name = f"{table_name}_{year}"
                start_val = f"{year}-01-01"
                end_val = f"{year + 1}-01-01"
                try:
                    conn.execute(text(
                        f"CREATE TABLE IF NOT EXISTS {partition_name} "
                        f"PARTITION OF {table_name} "
                        f"FOR VALUES FROM ('{start_val}') TO ('{end_val}')"
                    ))
                    click.echo(f"  Created partition: {partition_name}")
                except Exception as e:
                    if "already exists" in str(e):
                        click.echo(f"  Partition exists: {partition_name}")
                    else:
                        click.echo(f"  Error creating {partition_name}: {e}", err=True)

    # Create indexes
    click.echo("Creating indexes...")
    index_statements = [
        "CREATE INDEX IF NOT EXISTS idx_stocks_market ON stocks (market)",
        "CREATE INDEX IF NOT EXISTS idx_stocks_active ON stocks (is_active) WHERE is_active = TRUE",
        "CREATE INDEX IF NOT EXISTS idx_ohlcv_ticker ON daily_ohlcv (ticker, trade_date DESC)",
        "CREATE INDEX IF NOT EXISTS idx_fundamentals_ticker ON fundamentals (ticker, trade_date DESC)",
        "CREATE INDEX IF NOT EXISTS idx_investor_ticker ON investor_trading (ticker, trade_date DESC)",
        "CREATE INDEX IF NOT EXISTS idx_collection_log_date ON collection_log (target_date DESC)",
    ]

    with engine.begin() as conn:
        for stmt in index_statements:
            try:
                conn.execute(text(stmt))
            except Exception as e:
                click.echo(f"  Index warning: {e}", err=True)

    click.echo("Database initialization complete.")


if __name__ == "__main__":
    cli()
