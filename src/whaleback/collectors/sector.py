import logging
from datetime import date


from whaleback.api.krx_client import KRXClient
from whaleback.db.engine import get_session

logger = logging.getLogger(__name__)


class SectorCollector:
    """Collects sector classification for all stocks.

    Unlike date-based collectors, sector mapping is a reference table
    that gets fully refreshed on each run.
    """

    def __init__(self, client: KRXClient):
        self.client = client

    def run(self, target_date: date | None = None) -> int:
        """Fetch and persist sector mappings for all markets."""
        date_str = (target_date or date.today()).strftime("%Y%m%d")
        logger.info(f"Collecting sector mappings for {date_str}")

        rows = []
        for market in ("KOSPI", "KOSDAQ"):
            try:
                sector_map = self.client.get_market_sector_ticker_list(date_str, market)
                for sector_name, tickers in sector_map.items():
                    for ticker in tickers:
                        rows.append(
                            {
                                "ticker": ticker,
                                "sector": sector_name,
                                "sector_en": None,  # Can be filled later
                                "sub_sector": None,
                            }
                        )
            except Exception as e:
                logger.warning(f"Failed to get sector data for {market}: {e}")
                continue

        if not rows:
            logger.warning("No sector data collected")
            return 0

        # Deduplicate by ticker (some tickers may appear in multiple sector indices)
        seen = {}
        for row in rows:
            seen[row["ticker"]] = row
        unique_rows = list(seen.values())

        with get_session() as session:
            from whaleback.db.repositories import upsert_sector_mapping

            count = upsert_sector_mapping(unique_rows, session=session)

        logger.info(f"Upserted {count} sector mappings")
        return count
