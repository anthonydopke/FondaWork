# valuation.py
"""
Valuation helpers: multiples, EV calculation, relative comparison, and a high-level
function that runs both multiples and DCF and returns a consolidated valuation.
"""

from typing import Dict, Any, Optional
import math


def compute_ev(info: dict) -> Optional[float]:
    """Enterprise value = market cap + totalDebt - cash"""
    market_cap = info.get("marketCap")
    total_debt = info.get("totalDebt") or info.get("totalDebtLongTerm") or 0
    cash = info.get("totalCash") or info.get("cash") or 0
    if not market_cap:
        return None
    return float(market_cap + (total_debt or 0) - (cash or 0))


def compute_ev_ebitda(info: dict) -> Optional[float]:
    ev = compute_ev(info)
    ebitda = info.get("ebitda") or info.get("EBITDA")
    if ev is None or not ebitda or ebitda == 0:
        return None
    return float(ev / ebitda)


def simple_multiples_valuation(info: dict) -> Dict[str, Optional[float]]:
    """
    Return a dictionary of common multiples (PE, PB, PS, EV/EBITDA).
    Values are numeric (not 'Undervalued' strings) so the rating engine can compare vs peers.
    """
    result = {}
    result["PE"] = info.get("trailingPE") or info.get("forwardPE")
    result["PB"] = info.get("priceToBook")
    result["PS"] = info.get("priceToSalesTrailing12Months") or info.get("priceToSales")
    result["EV/EBITDA"] = compute_ev_ebitda(info)
    result["P/FCF"] = None
    # compute P/FCF if freeCashflow and shares/outstanding present
    fcf = info.get("freeCashflow")
    shares = info.get("sharesOutstanding")
    price = info.get("currentPrice")
    if fcf and shares and price:
        try:
            fcf_per_share = fcf / shares
            result["P/FCF"] = price / fcf_per_share if fcf_per_share != 0 else None
        except Exception:
            result["P/FCF"] = None
    return result


def consolidate_valuation(info: dict, fcf_now: float, forecast_growths: list = None, terminal_growth: float = 0.02, wacc: float = None):
    """
    High-level function:
    - computes simple multiples
    - runs a 2-stage DCF if possible, or 1-stage if only basics available
    - returns numeric intrinsic price, suggested buy price and multiples
    """
    from dcf import estimate_wacc, dcf_two_stage, dcf_one_stage, intrinsic_value_per_share_from_ev, margin_of_safety_price

    multiples = simple_multiples_valuation(info)
    # estimate wacc if not provided
    if wacc is None:
        wacc = estimate_wacc(info) or 0.08

    intrinsic_price = None
    ev_value = None
    # try two-stage if forecast growths supplied and fcf available
    try:
        if fcf_now and forecast_growths:
            ev_value = dcf_two_stage(fcf_now, forecast_growths, terminal_growth, wacc)
        elif fcf_now:
            ev_value = dcf_one_stage(fcf_now, terminal_growth, wacc)
    except Exception:
        ev_value = None

    if ev_value:
        intrinsic_price = intrinsic_value_per_share_from_ev(ev_value, info)

    suggested_buy = margin_of_safety_price(intrinsic_price, margin=0.20) if intrinsic_price else None

    return {
        "multiples": multiples,
        "wacc": wacc,
        "intrinsic_price": intrinsic_price,
        "suggested_buy_price": suggested_buy,
        "ev_value": ev_value
    }

def safe_intrinsic_price(info, dcf_price, multiples_price):
    """
    Produces a realistic entry price by combining DCF, multiples, and 
    sanity filters to avoid unrealistic valuations.
    """

    current = info.get("currentPrice")
    if current is None:
        return None

    prices = []

    # 1. Multiples are usually the most stable → high weight
    if multiples_price:
        prices.append(multiples_price * 0.6)

    # 2. DCF can be unstable → low weight
    if dcf_price:
        prices.append(dcf_price * 0.4)

    if not prices:
        return None

    fair_value = sum(prices)

    # === SANITY CHECKS ===

    # Prevent insane valuations (>200% of current price)
    if fair_value > current * 2:
        fair_value = (fair_value + current * 2) / 2

    # Prevent downward anomalies (<30% of current price)
    if fair_value < current * 0.3:
        fair_value = max(fair_value, current * 0.3)

    # Entry price = 20% safety margin
    entry_price = fair_value * 0.8

    return round(fair_value, 2), round(entry_price, 2)

