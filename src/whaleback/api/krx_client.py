import logging
import time

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)
from pykrx import stock
import pandas as pd

logger = logging.getLogger(__name__)


class KRXClient:
    """Rate-limited, retry-enabled wrapper around pykrx."""

    def __init__(self, delay: float = 1.0, max_retries: int = 3, backoff: float = 2.0):
        self._delay = delay
        self._max_retries = max_retries
        self._backoff = backoff
        self._last_request_time: float = 0.0

    def _rate_limit(self):
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._delay:
            time.sleep(self._delay - elapsed)
        self._last_request_time = time.monotonic()

    def _call(self, func, *args, **kwargs):
        @retry(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=self._backoff, min=2, max=60),
            retry=retry_if_exception_type((ConnectionError, TimeoutError)),
            before_sleep=before_sleep_log(logger, logging.WARNING),
        )
        def _inner():
            self._rate_limit()
            result = func(*args, **kwargs)
            return result

        return _inner()

    def get_ticker_list(self, date_str: str, market: str = "ALL") -> list[str]:
        return self._call(stock.get_market_ticker_list, date_str, market)

    def get_ticker_name(self, ticker: str) -> str:
        return self._call(stock.get_market_ticker_name, ticker)

    def get_ohlcv_by_date(self, date_str: str, market: str = "KOSPI") -> pd.DataFrame:
        """Get OHLCV for ALL tickers on a single date."""
        return self._call(stock.get_market_ohlcv_by_ticker, date_str, market)

    def get_ohlcv_by_ticker(self, start: str, end: str, ticker: str) -> pd.DataFrame:
        """Get OHLCV for a single ticker over date range."""
        return self._call(stock.get_market_ohlcv, start, end, ticker)

    def get_fundamentals_by_date(self, date_str: str, market: str = "ALL") -> pd.DataFrame:
        """Get fundamentals for ALL tickers on a single date. Returns DataFrame indexed by ticker."""
        return self._call(stock.get_market_fundamental, date_str, market=market)

    def get_investor_trading_by_ticker(self, start: str, end: str, ticker: str) -> pd.DataFrame:
        """Get investor net trading values for a single ticker over date range."""
        return self._call(stock.get_market_trading_value_by_date, start, end, ticker)

    def get_net_purchases_by_ticker(
        self, start: str, end: str, market: str = "KOSPI", investor: str = "개인"
    ) -> pd.DataFrame:
        """Get net purchases for all tickers by investor type. Returns DataFrame indexed by ticker."""
        return self._call(
            stock.get_market_net_purchases_of_equities_by_ticker, start, end, market, investor
        )

    def get_index_ohlcv_by_date(self, date_str: str, index_code: str = "1001") -> pd.DataFrame:
        """Get index OHLCV for a single date. Default: KOSPI (1001)."""
        return self._call(stock.get_index_ohlcv_by_date, date_str, date_str, index_code)

    def get_index_price_change(self, date_str: str, market: str = "KOSPI") -> pd.DataFrame:
        """Get index price changes including 등락률. Returns DataFrame indexed by 지수명."""
        return self._call(stock.get_index_price_change_by_ticker, date_str, date_str, market)

    def get_index_ticker_list(self, date_str: str, market: str = "KOSPI") -> list[str]:
        """Get index code list for a market."""
        return self._call(stock.get_index_ticker_list, date_str, market)

    def get_market_sector_ticker_list(
        self, date_str: str, market: str = "KOSPI"
    ) -> dict[str, list[str]]:
        """Get sector-to-ticker mapping. Returns dict: sector_name -> [ticker_list]."""
        df = self._call(stock.get_market_sector_classifications, date_str, market)
        if df is None or df.empty:
            return {}
        sectors: dict[str, list[str]] = {}
        for ticker, row in df.iterrows():
            sector_name = row["업종명"]
            if sector_name not in sectors:
                sectors[sector_name] = []
            sectors[sector_name].append(str(ticker))
        return sectors
