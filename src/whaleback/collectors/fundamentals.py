import logging
from datetime import date

import pandas as pd

from whaleback.collectors.base import BaseCollector
from whaleback.db.repositories import upsert_fundamentals

logger = logging.getLogger(__name__)


class FundamentalsCollector(BaseCollector):
    """Collects fundamental indicators (PER, PBR, EPS, DIV, BPS, DPS) + calculates ROE."""

    @property
    def collection_type(self) -> str:
        return "fundamentals"

    def fetch(self, date_str: str) -> pd.DataFrame:
        # Single API call returns all tickers' fundamentals for the date
        df = self.client.get_fundamentals_by_date(date_str, market="ALL")
        return df

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        # Calculate ROE: (EPS / BPS) * 100
        df["ROE"] = df.apply(
            lambda row: round((row["EPS"] / row["BPS"]) * 100, 4)
            if pd.notna(row.get("BPS")) and row.get("BPS", 0) != 0
            and pd.notna(row.get("EPS"))
            else None,
            axis=1,
        )

        # Drop rows where ALL fundamental values are zero/null (no data)
        fundamental_cols = ["BPS", "PER", "PBR", "EPS", "DIV", "DPS"]
        mask = df[fundamental_cols].apply(
            lambda row: not all(v == 0 or pd.isna(v) for v in row), axis=1
        )
        df = df[mask]

        return df

    def persist(self, df: pd.DataFrame, target_date: date, session) -> int:
        rows = []
        for ticker, row in df.iterrows():
            rows.append({
                "ticker": str(ticker),
                "trade_date": target_date,
                "bps": float(row["BPS"]) if pd.notna(row.get("BPS")) else None,
                "per": float(row["PER"]) if pd.notna(row.get("PER")) else None,
                "pbr": float(row["PBR"]) if pd.notna(row.get("PBR")) else None,
                "eps": float(row["EPS"]) if pd.notna(row.get("EPS")) else None,
                "div": float(row["DIV"]) if pd.notna(row.get("DIV")) else None,
                "dps": float(row["DPS"]) if pd.notna(row.get("DPS")) else None,
                "roe": float(row["ROE"]) if pd.notna(row.get("ROE")) else None,
            })

        return upsert_fundamentals(rows, session=session)
