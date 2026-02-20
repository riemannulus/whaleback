import logging
from datetime import date

import pandas as pd

from whaleback.collectors.base import BaseCollector
from whaleback.db.repositories import upsert_ohlcv

logger = logging.getLogger(__name__)

# pykrx Korean column names to English
OHLCV_COLUMNS = {
    "시가": "open",
    "고가": "high",
    "저가": "low",
    "종가": "close",
    "거래량": "volume",
    "거래대금": "trading_value",
    "등락률": "change_rate",
}


class OHLCVCollector(BaseCollector):
    """Collects daily OHLCV data for all stocks on a given date."""

    @property
    def collection_type(self) -> str:
        return "ohlcv"

    def fetch(self, date_str: str) -> pd.DataFrame:
        # Fetch all tickers for KOSPI and KOSDAQ separately, then combine
        frames = []
        for market in ("KOSPI", "KOSDAQ"):
            df = self.client.get_ohlcv_by_date(date_str, market)
            if df is not None and not df.empty:
                frames.append(df)

        if not frames:
            return pd.DataFrame()

        return pd.concat(frames)

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.rename(columns=OHLCV_COLUMNS)

        # Drop rows with zero close price (suspended/delisted)
        df = df[df["close"] > 0]

        # Ensure non-negative values
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df = df[df[col] >= 0]

        return df

    def persist(self, df: pd.DataFrame, target_date: date, session) -> int:
        rows = []
        for ticker, row in df.iterrows():
            rows.append({
                "ticker": str(ticker),
                "trade_date": target_date,
                "open": int(row["open"]) if pd.notna(row.get("open")) else None,
                "high": int(row["high"]) if pd.notna(row.get("high")) else None,
                "low": int(row["low"]) if pd.notna(row.get("low")) else None,
                "close": int(row["close"]),
                "volume": int(row["volume"]),
                "trading_value": int(row["trading_value"]) if pd.notna(row.get("trading_value")) else None,
                "change_rate": float(row["change_rate"]) if pd.notna(row.get("change_rate")) else None,
            })

        return upsert_ohlcv(rows, session=session)
