"""
Sector-aware valuation engine:
- Enterprise value & multiples
- Sector-adjusted multiples filtering
- DCF (1-stage or 2-stage)
- Final intrinsic price consolidation
"""

from typing import Dict, Any, Optional
import math


# ---------------------------------------------------------------------
#  ENTERPRISE VALUE / MULTIPLES
# ---------------------------------------------------------------------

def compute_ev(info: dict) -> Optional[float]:
    """Enterprise Value = Market Cap + Total Debt – Cash."""
    mc = info.get("marketCap")
    if not mc:
        return None

    debt = info.get("totalDebt") or info.get("totalDebtLongTerm") or 0
    cash = info.get("totalCash") or info.get("cash") or 0

    return float(mc + debt - cash)


def compute_ev_ebitda(info: dict) -> Optional[float]:
    """EV / EBITDA."""
    ev = compute_ev(info)
    ebitda = info.get("ebitda") or info.get("EBITDA")

    if ev is None or not ebitda:
        return None

    try:
        return float(ev / ebitda) if ebitda != 0 else None
    except Exception:
        return None


def base_multiples(info: dict) -> Dict[str, Optional[float]]:
    """
    Raw multiples extraction without sector logic.
    """
    out = {
        "PE": info.get("trailingPE") or info.get("forwardPE"),
        "PB": info.get("priceToBook"),
        "PS": info.get("priceToSalesTrailing12Months") or info.get("priceToSales"),
        "EV/EBITDA": compute_ev_ebitda(info),
        "P/FCF": None,
    }

    # Compute P/FCF
    fcf = info.get("freeCashflow")
    shares = info.get("sharesOutstanding")
    price = info.get("currentPrice")

    if fcf and shares and price:
        try:
            fcf_per_share = fcf / shares
            out["P/FCF"] = price / fcf_per_share if fcf_per_share != 0 else None
        except:
            pass

    return out


# ---------------------------------------------------------------------
#  SECTOR-AWARE MULTIPLES FILTERING
# ---------------------------------------------------------------------

def sector_adjusted_multiples(profile: dict, info: dict) -> Dict[str, Optional[float]]:
    """
    Filters multiples depending on the business sector.
    Example:
        - Banks: PB, PE only
        - Insurers: PB, Combined ratio later
        - Retail/Luxury: PE, EV/EBITDA, PS
        - Tech: P/FCF, PE, EV/EBITDA
    """

    raw = base_multiples(info)
    sector = profile.get("sector", "").lower()
    industry = profile.get("industry", "").lower()

    # --- Banking ---
    if "bank" in sector or "bank" in industry:
        return {
            "PE": raw["PE"],
            "PB": raw["PB"]
        }

    # --- Insurance ---
    if "insurance" in sector or "insurance" in industry:
        return {
            "PE": raw["PE"],
            "PB": raw["PB"]
        }

    # --- Real estate / REITs ---
    if "reit" in industry or "real estate" in sector:
        return {
            "PE": raw["PE"],
            "PB": raw["PB"],
            "EV/EBITDA": raw["EV/EBITDA"]
        }

    # --- Luxury / Consumer discretionary ---
    if "luxury" in industry or "apparel" in industry:
        return {
            "PE": raw["PE"],
            "EV/EBITDA": raw["EV/EBITDA"],
            "PS": raw["PS"]
        }

    # --- Technology ---
    if "technology" in sector or "software" in industry:
        return {
            "P/FCF": raw["P/FCF"],
            "EV/EBITDA": raw["EV/EBITDA"],
            "PE": raw["PE"]
        }

    # Default: return everything
    return raw


# ---------------------------------------------------------------------
#  CONSOLIDATED VALUATION
# ---------------------------------------------------------------------

def consolidate_valuation(
    info: dict,
    fcf_now: float,
    forecast_growths: list = None,
    terminal_growth: float = 0.02,
    wacc: float = None,
    profile: dict = None
):
    """
    Combines:
    - Sector-aware multiples
    - DCF (1-stage or 2-stage)
    Returns a dict used by main.py
    """

    from dcf import (
        estimate_wacc,
        dcf_two_stage,
        dcf_one_stage,
        intrinsic_value_per_share_from_ev,
        margin_of_safety_price
    )

    # --- Multiples ---
    if profile:
        multiples = sector_adjusted_multiples(profile, info)
    else:
        multiples = base_multiples(info)

    # --- WACC ---
    if wacc is None:
        wacc = estimate_wacc(info) or 0.08

    # --- DCF ---
    intrinsic_price = None
    ev_value = None

    try:
        if fcf_now and forecast_growths:
            ev_value = dcf_two_stage(fcf_now, forecast_growths, terminal_growth, wacc)
        elif fcf_now:
            ev_value = dcf_one_stage(fcf_now, terminal_growth, wacc)
    except Exception:
        ev_value = None

    if ev_value:
        intrinsic_price = intrinsic_value_per_share_from_ev(ev_value, info)

    suggested_buy = (
        margin_of_safety_price(intrinsic_price, margin=0.20)
        if intrinsic_price
        else None
    )

    return {
        "multiples": multiples,
        "wacc": wacc,
        "intrinsic_price": intrinsic_price,
        "suggested_buy_price": suggested_buy,
        "ev_value": ev_value
    }


# ---------------------------------------------------------------------
#  FAIR VALUE CONSOLIDATION (MULTIPLES + DCF)
# ---------------------------------------------------------------------

def safe_intrinsic_price(info, dcf_price, multiples_price):
    """
    Weighted fair value with sanity checks.
    """

    current = info.get("currentPrice")
    if current is None:
        return None

    prices = []

    # Multiples more stable → higher weight
    if multiples_price:
        prices.append(multiples_price * 0.6)

    # DCF volatile → lower weight
    if dcf_price:
        prices.append(dcf_price * 0.4)

    if not prices:
        return None

    fair_value = sum(prices)

    # --- Sanity filters ---
    if fair_value > current * 2:
        fair_value = (fair_value + current * 2) / 2

    if fair_value < current * 0.3:
        fair_value = max(fair_value, current * 0.3)

    entry_price = fair_value * 0.8

    return round(fair_value, 2), round(entry_price, 2)

def fair_value_from_multiples(info, multiples: dict, peer_medians: dict, profile: dict):
    """
    Computes fair value from sector-specific multiples.
    Works only if enough peer data is available.
    """

    price = info.get("currentPrice")
    if price is None:
        return None

    sector = profile.get("sector", "").lower()

    fair_values = []

    # === BANKS (PB & PE only) ===
    if "bank" in sector:
        bvps = info.get("bookValue")
        eps = info.get("epsTrailingTwelveMonths")

        # PB fair value
        if bvps and peer_medians.get("PB"):
            fair_values.append(peer_medians["PB"] * bvps)

        # PE fair value
        if eps and peer_medians.get("PE"):
            fair_values.append(peer_medians["PE"] * eps)

        if fair_values:
            return sum(fair_values) / len(fair_values)

        return None

    # === Default sectors ===
    # Weighted fair value from available multiples
    for key, mult in multiples.items():
        if mult and peer_medians.get(key):
            try:
                fv = price * (peer_medians[key] / mult)
                fair_values.append(fv)
            except:
                pass

    return sum(fair_values) / len(fair_values) if fair_values else None
