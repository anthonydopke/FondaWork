# dcf.py
"""
Discounted Cash Flow implementations:
- simple 1-phase perpetuity DCF
- 2-phase DCF with explicit forecast years then terminal value (Gordon growth)
Also contains a simple WACC estimator and helper utilities.
"""

from typing import Optional, List
import math


def estimate_wacc(info: dict, rf: float = 0.03, market_premium: float = 0.055, tax_rate: float = 0.25) -> Optional[float]:
    """
    A simple WACC estimator:
    - cost of equity = rf + beta * market_premium
    - cost of debt ~ implied or default (use 4%)
    - weights from marketCap and netDebt
    """
    try:
        beta = info.get("beta") or 1.0
        market_cap = info.get("marketCap")
        total_debt = info.get("totalDebt") or info.get("totalDebt") or 0
        cash = info.get("cash") or info.get("totalCash") or 0
        net_debt = max(0, (total_debt or 0) - (cash or 0))

        cost_of_equity = rf + float(beta) * market_premium
        cost_of_debt = info.get("interestRate") or 0.04  # fallback
        # after-tax cost of debt
        kd = float(cost_of_debt) * (1 - tax_rate)

        # weights
        if not market_cap:
            # can't compute WACC without market cap; return cost_of_equity as fallback
            return cost_of_equity
        ev_equity = float(market_cap)
        ev_debt = float(net_debt)
        total = ev_equity + ev_debt
        if total == 0:
            return cost_of_equity
        we = ev_equity / total
        wd = ev_debt / total

        wacc = we * cost_of_equity + wd * kd
        return float(wacc)
    except Exception:
        return None


def dcf_one_stage(fcf_now: float, growth: float, wacc: float) -> Optional[float]:
    """
    Perpetuity-form DCF: intrinsic value of firm = FCF_1 / (WACC - g)
    fcf_now: most recent FCF (not FCF_1)
    growth: decimal (e.g. 0.02)
    wacc: decimal
    Returns enterprise value (not per share).
    """
    if fcf_now is None or wacc is None:
        return None
    fcf1 = fcf_now * (1 + growth)
    denom = (wacc - growth)
    if denom <= 0:
        return None
    return fcf1 / denom


def dcf_two_stage(initial_fcf: float, forecast_growths: List[float], terminal_growth: float, wacc: float) -> Optional[float]:
    """
    Two-stage DCF:
    - forecast_growths: list of growth rates (decimal) for years 1..n
    - terminal_growth: g (decimal)
    - initial_fcf: the most recent FCF
    Returns PV of all cash flows (enterprise value).
    """
    if initial_fcf is None or wacc is None or not forecast_growths:
        return None
    fcf = float(initial_fcf)
    pv = 0.0
    for i, g in enumerate(forecast_growths, start=1):
        fcf = fcf * (1 + g)
        pv += fcf / ((1 + wacc) ** i)
    # terminal value at year n
    terminal_fcf = fcf * (1 + terminal_growth)
    terminal_value = terminal_fcf / (wacc - terminal_growth) if (wacc - terminal_growth) > 0 else None
    if terminal_value is None:
        return None
    pv += terminal_value / ((1 + wacc) ** len(forecast_growths))
    return pv


def intrinsic_value_per_share_from_ev(ev: float, info: dict) -> Optional[float]:
    """
    Convert enterprise value to per-share intrinsic price.
    Uses sharesOutstanding from info.
    """
    if ev is None or info is None:
        return None
    shares = info.get("sharesOutstanding")
    if not shares:
        # fallback: compute from marketCap / currentPrice
        market_cap = info.get("marketCap")
        price = info.get("currentPrice")
        if market_cap and price:
            try:
                shares = market_cap / price
            except Exception:
                shares = None
    if not shares or shares == 0:
        return None
    return float(ev / shares)


def margin_of_safety_price(intrinsic_price: float, margin: float = 0.20) -> Optional[float]:
    """Return the target buy price given a margin of safety (default 20%)."""
    if intrinsic_price is None:
        return None
    return round(intrinsic_price * (1 - margin), 2)
