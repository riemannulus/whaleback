import logging
from datetime import date

import pandas as pd

from whaleback.collectors.base import BaseCollector
from whaleback.db.repositories import upsert_investor_trading

logger = logging.getLogger(__name__)

# Investor types to collect, mapped to DB column names
INVESTOR_TYPES = {
    "연기금": "pension_net",
    "외국인": "foreign_net",
    "기관합계": "institution_net",
    "개인": "individual_net",
}


class InvestorTradingCollector(BaseCollector):
    """Collects investor trading data (net purchases) per ticker.

    Uses get_market_net_purchases_of_equities_by_ticker which returns
    all tickers for a given investor type in a single API call.
    Total: 4 investor types x 2 markets = 8 API calls (instead of 2700+ per-ticker calls).
    """

    @property
    def collection_type(self) -> str:
        return "investor"

    def fetch(self, date_str: str) -> pd.DataFrame:
        # Collect net purchase amounts per investor type across all tickers
        # Key: ticker -> {column: value}
        merged: dict[str, dict[str, int | None]] = {}

        for market in ("KOSPI", "KOSDAQ"):
            for investor_kr, col_name in INVESTOR_TYPES.items():
                try:
                    df = self.client.get_net_purchases_by_ticker(
                        date_str, date_str, market, investor_kr
                    )
                    if df is None or df.empty:
                        continue

                    for ticker, row in df.iterrows():
                        ticker_str = str(ticker)
                        if ticker_str not in merged:
                            merged[ticker_str] = {}
                        # 순매수거래대금 = net purchase value (in won)
                        val = row.get("순매수거래대금")
                        if pd.notna(val):
                            merged[ticker_str][col_name] = int(val)

                except Exception as e:
                    logger.warning(f"Failed to get {investor_kr} data for {market}: {e}")
                    continue

        if not merged:
            return pd.DataFrame()

        rows = []
        for ticker, data in merged.items():
            record = {"ticker": ticker}
            for col in INVESTOR_TYPES.values():
                record[col] = data.get(col)
            rows.append(record)

        return pd.DataFrame(rows)

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        investor_cols = [v for v in INVESTOR_TYPES.values() if v in df.columns]
        if investor_cols:
            mask = df[investor_cols].apply(
                lambda row: not all(v == 0 or pd.isna(v) for v in row), axis=1
            )
            df = df[mask]
        return df

    def persist(self, df: pd.DataFrame, target_date: date, session) -> int:
        rows = []
        for _, row in df.iterrows():
            record = {
                "ticker": str(row["ticker"]),
                "trade_date": target_date,
            }
            for col in INVESTOR_TYPES.values():
                val = row.get(col)
                record[col] = int(val) if pd.notna(val) else None

            # Columns not collected in this approach - set to None
            record.setdefault("financial_invest_net", None)
            record.setdefault("insurance_net", None)
            record.setdefault("trust_net", None)
            record.setdefault("private_equity_net", None)
            record.setdefault("bank_net", None)
            record.setdefault("other_financial_net", None)
            record.setdefault("other_corp_net", None)
            record.setdefault("other_foreign_net", None)
            record.setdefault("total_net", None)
            rows.append(record)

        return upsert_investor_trading(rows, session=session)
