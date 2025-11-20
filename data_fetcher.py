# data_fetcher.py
"""
Robust data fetcher for yfinance tickers.
Tries multiple endpoints because different tickers (especially non-US)
expose different fields. Returns cleaned pandas DataFrames and an `info` dict.
"""

import yfinance as yf
import pandas as pd
from typing import Tuple, Dict, Any


class DataFetcher:
    def __init__(self, ticker: str):
        self.ticker_str = ticker
        self.asset = yf.Ticker(ticker)

    def _safe_df(self, getter_name: str) -> pd.DataFrame:
        """Call a yfinance attribute or method and return a transposed, sorted DataFrame or empty."""
        try:
            obj = getattr(self.asset, getter_name)
            # some are methods
            if callable(obj):
                df = obj()
            else:
                df = obj
            if isinstance(df, pd.DataFrame) and not df.empty:
                df = df.T
                try:
                    df.index = pd.to_datetime(df.index)
                except Exception:
                    pass
                return df.sort_index()
        except Exception:
            pass
        return pd.DataFrame()

    def get_income(self) -> pd.DataFrame:
        # try several common yfinance attributes
        for name in ("financials", "get_income_stmt", "income_stmt", "get_financials"):
            df = self._safe_df(name)
            if not df.empty:
                return df
        return pd.DataFrame()

    def get_balance(self) -> pd.DataFrame:
        for name in ("balance_sheet", "get_balance_sheet", "balance"):
            df = self._safe_df(name)
            if not df.empty:
                return df
        return pd.DataFrame()

    def get_cashflow(self) -> pd.DataFrame:
        for name in ("cashflow", "get_cashflow"):
            df = self._safe_df(name)
            if not df.empty:
                return df
        return pd.DataFrame()

    def get_quarterly_income(self) -> pd.DataFrame:
        try:
            df = self.asset.quarterly_financials.T
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df.sort_index()
        except Exception:
            pass
        return pd.DataFrame()

    def get_info(self) -> Dict[str, Any]:
        try:
            info = self.asset.info or {}
            return info
        except Exception:
            return {}

    def validate_ticker(self) -> bool:
        """A basic validation: does asset have a marketCap or currentPrice?"""
        info = self.get_info()
        return bool(info.get("marketCap") or info.get("currentPrice"))
