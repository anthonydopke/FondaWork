# ==============================================
# === fundamental_analysis.py
# ==============================================

"""
Module: fundamental_analysis
Processes raw financial data to compute fundamental indicators.
"""

import numpy as np

class FundamentalAnalysis:
    """Computes fundamental ratios and growth metrics from financial statements."""

    def __init__(self, income_df, balance_df, cashflow_df, info: dict):
        self.income = income_df
        self.balance = balance_df
        self.cashflow = cashflow_df
        self.info = info

    # ------------- Growth Analysis -------------
    def compute_revenue_growth(self):
        if self.income.empty or "Total Revenue" not in self.income:
            return None
        return self.income["Total Revenue"].pct_change().mean() * 100

    def compute_net_income_growth(self):
        if self.income.empty or "Net Income" not in self.income:
            return None
        return self.income["Net Income"].pct_change().mean() * 100

    # ------------- Profitability -------------
    def get_operating_margin(self):
        return self.info.get("operatingMargins", None)

    def get_net_margin(self):
        return self.info.get("profitMargins", None)

    def get_roe(self):
        return self.info.get("returnOnEquity", None)

    def get_roa(self):
        return self.info.get("returnOnAssets", None)

    # ------------- Financial Health -------------
    def get_debt_to_equity(self):
        return self.info.get("debtToEquity", None)

    def get_current_ratio(self):
        return self.info.get("currentRatio", None)

    # ------------- Valuation -------------
    def get_pe_ratio(self):
        return self.info.get("trailingPE", None)

    def get_price_to_book(self):
        return self.info.get("priceToBook", None)

    def get_price_to_sales(self):
        return self.info.get("priceToSalesTrailing12Months", None)


