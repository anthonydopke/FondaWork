# profitability.py
"""
Compute ROIC, NOPAT, margins and earnings quality indicators.
ROIC calculation attempts to use operating income and invested capital from balance sheet.
"""

from typing import Optional
import pandas as pd
import numpy as np


def safe_get(series: pd.Series, keys):
    """Return first available column from keys in series (DataFrame)."""
    for k in keys:
        if k in series:
            return series[k]
    return None


def compute_operating_margin(info: dict) -> Optional[float]:
    """Return operating margin (decimal), if available from info."""
    val = info.get("operatingMargins") or info.get("operatingMargin")
    return float(val) if val is not None else None


def compute_net_margin(info: dict) -> Optional[float]:
    val = info.get("profitMargins") or info.get("profitMargin")
    return float(val) if val is not None else None


def compute_roe(info: dict) -> Optional[float]:
    val = info.get("returnOnEquity") or info.get("roe")
    return float(val) if val is not None else None


def compute_roa(info: dict) -> Optional[float]:
    val = info.get("returnOnAssets") or info.get("roa")
    return float(val) if val is not None else None


def compute_nopat_from_income(income_df: pd.DataFrame, tax_rate: float = 0.25) -> Optional[float]:
    """
    Estimate NOPAT from income statement: use 'Operating Income' or 'EBIT'.
    Returns the most recent NOPAT (scalar).
    """
    if income_df is None or income_df.empty:
        return None
    for col in ["Operating Income", "OperatingIncome", "operatingIncome", "EBIT", "Ebit"]:
        if col in income_df.columns:
            op_income = income_df[col].dropna()
            if not op_income.empty:
                # take most recent
                ebit = float(op_income.iloc[-1])
                return ebit * (1 - tax_rate)
    return None


def compute_invested_capital(balance_df: pd.DataFrame) -> Optional[float]:
    """
    Rough invested capital: total assets - current liabilities - excess cash.
    We try common names from balance sheet.
    """
    if balance_df is None or balance_df.empty:
        return None
    # try for Total Assets
    assets_cols = ["Total Assets", "totalAssets", "Assets"]
    liabilities_cols = ["Total Current Liabilities", "Total Liab", "totalLiab"]
    cash_keys = ["Cash And Cash Equivalents", "Cash", "cash"]

    assets = None
    liabilities = None
    cash = 0.0

    for k in assets_cols:
        if k in balance_df.columns:
            s = balance_df[k].dropna()
            if not s.empty:
                assets = float(s.iloc[-1])
                break

    for k in liabilities_cols:
        if k in balance_df.columns:
            s = balance_df[k].dropna()
            if not s.empty:
                liabilities = float(s.iloc[-1])
                break

    for k in cash_keys:
        if k in balance_df.columns:
            s = balance_df[k].dropna()
            if not s.empty:
                cash = float(s.iloc[-1])
                break

    if assets is None:
        return None

    if liabilities is None:
        # fallback to totalDebt if present
        return assets

    invested = assets - liabilities - cash
    # invested should be positive
    return float(max(invested, np.nanmean([assets, 0])))
    

def compute_roic(income_df, balance_df, info: dict, tax_rate: float = 0.25) -> Optional[float]:
    """
    Compute ROIC = NOPAT / Invested Capital. Both numerator and denominator estimated from statements.
    Returns decimal (e.g. 0.12 for 12%).
    """
    nopat = compute_nopat_from_income(income_df, tax_rate=tax_rate)
    invested = compute_invested_capital(balance_df)
    if nopat is None or invested is None or invested == 0:
        # fallback: try to use info fields if present
        roic_info = info.get("returnOnCapitalEmployed") or info.get("returnOnInvestedCapital")
        if roic_info:
            return float(roic_info)
        return None
    return float(nopat / invested)
