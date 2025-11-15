
# ==============================================
# === data_fetcher.py
# ==============================================

"""
Module: data_fetcher
Responsible for fetching all relevant financial data used for fundamental analysis.
Comments and method names are in English.
"""

import yfinance as yf
import pandas as pd
import numpy as np

class DataFetcher:
    """Fetches financial statements and market data for a given stock ticker."""

    def __init__(self, ticker: str):
        self.ticker = ticker
        self.asset = yf.Ticker(ticker)

    def get_income_statement(self) -> pd.DataFrame:
        """Return income statement as a cleaned pandas DataFrame."""
        try:
            df = self.asset.get_income_stmt().T
            df.index = pd.to_datetime(df.index)
            return df.sort_index()
        except:
            return pd.DataFrame()

    def get_balance_sheet(self) -> pd.DataFrame:
        """Return balance sheet."""
        try:
            df = self.asset.get_balance_sheet().T
            df.index = pd.to_datetime(df.index)
            return df.sort_index()
        except:
            return pd.DataFrame()

    def get_cashflow(self) -> pd.DataFrame:
        """Return cashflow statement."""
        try:
            df = self.asset.get_cashflow().T
            df.index = pd.to_datetime(df.index)
            return df.sort_index()
        except:
            return pd.DataFrame()

    def get_info(self) -> dict:
        """Return general financial info such as PE, margins, etc."""
        return self.asset.info if self.asset.info else {}


