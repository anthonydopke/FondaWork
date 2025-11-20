# growth.py
"""
Compute historical growth rates for revenue and net income
in a robust way using the income DataFrame returned by DataFetcher.
"""

import pandas as pd
import numpy as np
from typing import Optional


def pct_mean(series: pd.Series, periods: int = None) -> Optional[float]:
    """
    Compute average annual growth rate (simple arithmetic mean of yearly pct_change).
    Returns percentage (e.g. 8.5 for 8.5%).
    """
    if series is None or series.empty:
        return None
    try:
        # drop zeros and NaNs to avoid infinite pct_change
        s = series.replace([0], np.nan).dropna()
        if s.shape[0] < 2:
            return None
        changes = s.pct_change().dropna()
        if changes.empty:
            return None
        # optionally limit to the most recent `periods` years
        if periods:
            changes = changes.tail(periods)
        return float(changes.mean() * 100)
    except Exception:
        return None


def get_revenue_series(income_df: pd.DataFrame) -> pd.Series:
    """Try several common revenue column names used by yfinance."""
    if income_df is None or income_df.empty:
        return pd.Series(dtype=float)
    for name in ["Total Revenue", "Revenue", "totalRevenue", "Net Sales", "Revenues"]:
        if name in income_df.columns:
            return income_df[name].dropna()
    # fallback: try first numeric column
    numeric_cols = [c for c in income_df.columns if pd.api.types.is_numeric_dtype(income_df[c])]
    if numeric_cols:
        return income_df[numeric_cols[0]].dropna()
    return pd.Series(dtype=float)


def get_net_income_series(income_df: pd.DataFrame) -> pd.Series:
    """Try several common net income column names."""
    if income_df is None or income_df.empty:
        return pd.Series(dtype=float)
    for name in ["Net Income", "Net Income Common Stocks", "netIncome", "Net Income Applicable To Common Shares"]:
        if name in income_df.columns:
            return income_df[name].dropna()
    numeric_cols = [c for c in income_df.columns if pd.api.types.is_numeric_dtype(income_df[c])]
    if numeric_cols:
        return income_df[numeric_cols[-1]].dropna()  # last numeric column often net income
    return pd.Series(dtype=float)


def compute_revenue_growth(income_df: pd.DataFrame, years: int = 5) -> Optional[float]:
    series = get_revenue_series(income_df)
    return pct_mean(series, periods=years)


def compute_net_income_growth(income_df: pd.DataFrame, years: int = 5) -> Optional[float]:
    series = get_net_income_series(income_df)
    return pct_mean(series, periods=years)
