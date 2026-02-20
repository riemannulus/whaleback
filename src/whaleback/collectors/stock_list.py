import logging
from datetime import date

import pandas as pd

from whaleback.collectors.base import BaseCollector
from whaleback.db.engine import get_session
from whaleback.db.repositories import get_active_tickers, upsert_stocks

logger = logging.getLogger(__name__)


class StockListCollector(BaseCollector):
    """Syncs the stock master table with KRX listings.

    Detects new listings (in KRX but not in DB) and delistings
    (in DB active but not in KRX).
    """

    @property
    def collection_type(self) -> str:
        return "stock_sync"

    def fetch(self, date_str: str) -> pd.DataFrame:
        records = []
        for market in ("KOSPI", "KOSDAQ"):
            tickers = self.client.get_ticker_list(date_str, market)
            for ticker in tickers:
                records.append({"ticker": ticker, "market": market})

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)

        # Fetch names only for new tickers (not already in DB)
        with get_session() as session:
            existing = get_active_tickers(session)

        new_tickers = [r["ticker"] for r in records if r["ticker"] not in existing]

        # For existing tickers, use cached names
        name_map = {ticker: stock.name for ticker, stock in existing.items()}

        # Bulk fetch names for new tickers (no rate limiting needed)
        if new_tickers:
            logger.info(f"Fetching names for {len(new_tickers)} new tickers...")
            bulk_names = self.client.get_ticker_names_bulk(new_tickers)
            name_map.update(bulk_names)

        df["name"] = df["ticker"].map(name_map)
        return df

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.dropna(subset=["ticker", "market"])
        df = df[df["ticker"].str.len() == 6]
        return df

    def persist(self, df: pd.DataFrame, target_date: date, session) -> int:
        changes = 0

        existing = get_active_tickers(session)
        krx_tickers = set(df["ticker"].tolist())
        db_tickers = set(existing.keys())

        # NEW LISTINGS
        new_tickers = krx_tickers - db_tickers
        if new_tickers:
            new_df = df[df["ticker"].isin(new_tickers)]
            new_stocks = [
                {
                    "ticker": row["ticker"],
                    "name": row["name"],
                    "market": row["market"],
                    "is_active": True,
                    "listed_date": target_date,
                }
                for _, row in new_df.iterrows()
            ]
            upsert_stocks(new_stocks, session=session)
            logger.info(f"New listings: {len(new_stocks)} stocks")
            changes += len(new_stocks)

        # DELISTINGS
        delisted = db_tickers - krx_tickers
        if delisted:
            for ticker in delisted:
                stock = existing[ticker]
                stock.is_active = False
                stock.delisted_date = target_date
            logger.info(f"Delistings: {len(delisted)} stocks")
            changes += len(delisted)

        # NAME UPDATES for existing active stocks
        for ticker in krx_tickers & db_tickers:
            row = df[df["ticker"] == ticker].iloc[0]
            if existing[ticker].name != row["name"]:
                existing[ticker].name = row["name"]
                changes += 1

        session.flush()
        return changes
