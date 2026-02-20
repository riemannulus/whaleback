import logging
from datetime import date

import pandas as pd

from whaleback.collectors.base import BaseCollector
from whaleback.db.repositories import upsert_market_index

logger = logging.getLogger(__name__)

# Major indices to collect
INDICES = {
    "1001": "코스피",
    "2001": "코스닥",
}


class IndexCollector(BaseCollector):
    """Collects daily OHLCV data for major market indices (KOSPI, KOSDAQ)."""

    @property
    def collection_type(self) -> str:
        return "market_index"

    def fetch(self, date_str: str) -> pd.DataFrame:
        rows = []
        # Fetch price changes per market (includes 등락률)
        market_map = {"KOSPI": ("1001", "코스피"), "KOSDAQ": ("2001", "코스닥")}
        for market, (index_code, index_name) in market_map.items():
            try:
                df = self.client.get_index_price_change(date_str, market)
                if df is not None and not df.empty and index_name in df.index:
                    row_data = df.loc[index_name]
                    rows.append(
                        {
                            "index_code": index_code,
                            "index_name": index_name,
                            "close": float(row_data.get("종가", 0)),
                            "change_rate": float(row_data.get("등락률", 0)),
                            "volume": int(row_data.get("거래량", 0)),
                            "trading_value": int(row_data.get("거래대금", 0)),
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to get index data for {index_code} ({index_name}): {e}")
                continue

        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows)

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" in df.columns:
            df = df[df["close"] > 0]
        return df

    def persist(self, df: pd.DataFrame, target_date: date, session) -> int:
        rows = []
        for _, row in df.iterrows():
            rows.append(
                {
                    "trade_date": target_date,
                    "index_code": str(row["index_code"]),
                    "index_name": str(row["index_name"]),
                    "close": float(row["close"]),
                    "change_rate": float(row["change_rate"])
                    if pd.notna(row.get("change_rate"))
                    else None,
                    "volume": int(row["volume"]) if pd.notna(row.get("volume")) else None,
                    "trading_value": int(row["trading_value"])
                    if pd.notna(row.get("trading_value"))
                    else None,
                }
            )
        return upsert_market_index(rows, session=session)
