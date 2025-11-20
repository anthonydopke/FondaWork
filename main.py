# main.py
"""
Main CLI orchestrator for FondaWork (Sector-aware version).
Handles ticker resolution, data fetch, sector profiles, fundamentals,
valuation, ratings, and peer comparisons.
"""

from data_fetcher import DataFetcher
from sector_profiles import SectorProfiles

from growth import compute_revenue_growth, compute_net_income_growth
from profitability import (
    compute_operating_margin, compute_net_margin,
    compute_roic, compute_roe, compute_roa
)
from valuation import consolidate_valuation, fair_value_from_multiples, safe_intrinsic_price
from rating_engine import RatingEngine
from ticker_resolver import TickerResolver
from industry import peers_median

import json


# ------------------------------------------------------
# Formatting helpers
# ------------------------------------------------------
def fmt(x):
    try:
        return f"{float(x):.2f}"
    except Exception:
        return str(x)

def fmt_pct(x):
    try:
        return f"{float(x):.2f}%"
    except Exception:
        return str(x)


# ------------------------------------------------------
# MAIN PIPELINE
# ------------------------------------------------------
def run():
    # --------------------------------------------------
    # 1) Ticker resolution
    # --------------------------------------------------
    user_input = input("Enter stock name or ticker: ").strip()

    resolver = TickerResolver()
    ticker = resolver.resolve(user_input)


    # --------------------------------------------------
    # 2) Fetch data
    # --------------------------------------------------
    fetcher = DataFetcher(ticker)

    if not fetcher.validate_ticker():
        print("Ticker validation failed or no market data available.")
        return

    income = fetcher.get_income()
    balance = fetcher.get_balance()
    cash = fetcher.get_cashflow()
    info = fetcher.get_info()

    # --------------------------------------------------
    # 3) Determine SECTOR PROFILE
    # --------------------------------------------------
    profile = SectorProfiles.get_profile(info)
    enabled = profile["metrics"]
    thresholds = profile["thresholds"]
    weights = profile["weights"]
    preferred_multiples = profile["preferred_multiples"]

    # --------------------------------------------------
    # 4) Compute only enabled metrics
    # --------------------------------------------------
    metrics = {}

    if enabled.get("revenue_growth"):
        metrics["revenue_growth"] = compute_revenue_growth(income, years=5)

    if enabled.get("net_income_growth"):
        metrics["net_income_growth"] = compute_net_income_growth(income, years=5)

    if enabled.get("operating_margin"):
        metrics["operating_margin"] = compute_operating_margin(info)

    if enabled.get("net_margin"):
        metrics["net_margin"] = compute_net_margin(info)

    if enabled.get("roe"):
        metrics["roe"] = compute_roe(info)

    if enabled.get("roa"):
        metrics["roa"] = compute_roa(info)

    if enabled.get("roic"):
        metrics["roic"] = compute_roic(income, balance, info)

    # --------------------------------------------------
    # 5) Extract Free Cash Flow (FCF) if needed
    # --------------------------------------------------
    fcf = None
    if enabled.get("fcf"):
        try:
            if not cash.empty:
                for col in ["Free Cash Flow", "FreeCashFlow", "freeCashflow"]:
                    if col in cash.columns and not cash[col].dropna().empty:
                        fcf = float(cash[col].dropna().iloc[-1])
                        break

                if fcf is None:
                    cfo = None
                    capex = None

                    for k in ["Total Cash From Operating Activities",
                              "Operating Cash Flow", "cashFlowFromOperations"]:
                        if k in cash.columns and not cash[k].dropna().empty:
                            cfo = float(cash[k].dropna().iloc[-1])
                            break

                    for k in ["Capital Expenditures",
                              "capitalExpenditures", "Capex"]:
                        if k in cash.columns and not cash[k].dropna().empty:
                            capex = float(cash[k].dropna().iloc[-1])
                            break

                    if cfo is not None:
                        fcf = cfo - (capex or 0)
        except Exception:
            fcf = None

        metrics["fcf"] = fcf

    # --------------------------------------------------
    # 6) Peer tickers
    # --------------------------------------------------
    peer_input = input("Optional: peer tickers (comma-separated): ").strip()
    raw_peers = [p.strip() for p in peer_input.split(',')] if peer_input else []
    peers = []

    for p in raw_peers:
        try:
            peers.append(resolver.resolve(p))
        except Exception:
            print(f"Warning: unable to resolve peer '{p}'. Skipping.")

    # --------------------------------------------------
    # 7) Valuation (sector-aware)
    # --------------------------------------------------
    valuation = consolidate_valuation(
        info,
        fcf_now=fcf,
        forecast_growths=[0.08] * 5 if fcf else None,
        terminal_growth=0.02,
        wacc=None,
        profile=profile  
    )


    peer_medians = peers_median(peers, ["PE", "PB", "EV/EBITDA"]) if peers else {}

    # --------------------------------------------------
    # 8) Ratings using sector-specific thresholds
    # --------------------------------------------------
    ratings = {}
    for name, value in metrics.items():
        if name in thresholds:
            low, mid = thresholds[name]
            ratings[name] = RatingEngine.rate_value(value, (low, mid))
        else:
            ratings[name] = RatingEngine.rate_value(value)

    # Compute global score with sector weights
    global_score = RatingEngine.compute_global_score(ratings, weights)

    # --------------------------------------------------
    # 9) Build final report
    # --------------------------------------------------
    report = []
    report.append(f"\nFundamental & Sector-Aware Valuation for {ticker}")
    report.append("=" * 65)
    report.append(f"\nDetected Sector: {profile['sector']}")

    report.append("\n-- Key Indicators --")
    for k, v in metrics.items():
        line = f"{k}: {fmt_pct(v*100) if isinstance(v, float) else fmt(v)}"
        report.append(line)

    report.append("\n-- Ratings (sector-adjusted) --")
    for k, v in ratings.items():
        report.append(f"{k}: {v}")

    report.append(f"\nGlobal Score (sector-weighted): {global_score}/100")

    report.append("\n-- Valuation --")
    if valuation.get("wacc"):
        report.append(f"WACC used: {fmt_pct(valuation['wacc']*100)}")

    report.append(f"Preferred multiples: {preferred_multiples}")
    for k, v in valuation.get("multiples", {}).items():
        report.append(f"{k}: {fmt(v)}")


    multiples_fair = fair_value_from_multiples(info, 
                                           valuation["multiples"], 
                                           peer_medians, 
                                           profile)

    fair_combo = safe_intrinsic_price(
        info,
        valuation.get("intrinsic_price"),
        multiples_fair
    )

    if fair_combo:
        fair, entry = fair_combo
        report.append(f"Fair value (combined): {fair}")
        report.append(f"Entry price (20% safety margin): {entry}")
    else:
        report.append("Fair value (combined): N/A")
        report.append("Entry price (20% safety margin): N/A")

    report.append(f"Current market price: {info.get('currentPrice')}")

    if peers:
        report.append("\n-- Peer Medians --")
        report.append(json.dumps(peer_medians, indent=2))

    print("\n".join(report))


# ------------------------------------------------------
# RUN
# ------------------------------------------------------
if __name__ == "__main__":
    run()
