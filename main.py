# main.py
"""
Main CLI orchestrator for FondaWork (Option 3).
Handles: ticker resolution, data fetch, fundamentals, valuation, ratings, peers.
"""

from data_fetcher import DataFetcher
from growth import compute_revenue_growth, compute_net_income_growth
from profitability import (
    compute_operating_margin, compute_net_margin,
    compute_roic, compute_roe, compute_roa
)
from valuation import consolidate_valuation, safe_intrinsic_price
from rating_engine import RatingEngine
from ticker_resolver import TickerResolver
from industry import peers_median

import json

def fmt(x):
    """Format floats to 2 decimals."""
    try:
        return f"{float(x):.2f}"
    except:
        return str(x)

def fmt_pct(x):
    """Format percent values: 12.34%."""
    try:
        return f"{float(x):.2f}%"
    except:
        return str(x)


def format_pct(x):
    return f"{x:.2f}%" if isinstance(x, float) else str(x)


def run():
    # -----------------------------
    # 1) Resolve ticker
    # -----------------------------
    user_input = input("Enter stock name or ticker: ").strip()

    resolver = TickerResolver()
    ticker = resolver.resolve(user_input)
    print(f"Resolved ticker: {ticker}")

    # -----------------------------
    # 2) Fetch market data
    # -----------------------------
    fetcher = DataFetcher(ticker)

    if not fetcher.validate_ticker():
        print("Ticker validation failed or no market data available.")
        return

    income = fetcher.get_income()
    balance = fetcher.get_balance()
    cash = fetcher.get_cashflow()
    info = fetcher.get_info()

    # -----------------------------
    # 3) Growth metrics
    # -----------------------------
    rev_growth = compute_revenue_growth(income, years=5)
    ni_growth = compute_net_income_growth(income, years=5)

    # -----------------------------
    # 4) Profitability
    # -----------------------------
    op_margin = compute_operating_margin(info)
    net_margin = compute_net_margin(info)
    roe = compute_roe(info)
    roa = compute_roa(info)
    roic = compute_roic(income, balance, info)

    # -----------------------------
    # 5) Free Cash Flow extraction
    # -----------------------------
    fcf = None
    try:
        if not cash.empty:
            # Direct FCF keys
            for col in ["Free Cash Flow", "FreeCashFlow", "freeCashflow"]:
                if col in cash.columns and not cash[col].dropna().empty:
                    fcf = float(cash[col].dropna().iloc[-1])
                    break

            # Fallback CFO - Capex
            if fcf is None:
                cfo_keys = [
                    "Total Cash From Operating Activities",
                    "Operating Cash Flow",
                    "cashFlowFromOperations"
                ]
                capex_keys = [
                    "Capital Expenditures",
                    "capitalExpenditures",
                    "Capex"
                ]

                cfo = None
                capex = None

                for k in cfo_keys:
                    if k in cash.columns and not cash[k].dropna().empty:
                        cfo = float(cash[k].dropna().iloc[-1])
                        break

                for k in capex_keys:
                    if k in cash.columns and not cash[k].dropna().empty:
                        capex = float(cash[k].dropna().iloc[-1])
                        break

                if cfo is not None:
                    fcf = cfo - (capex or 0)
    except Exception:
        fcf = None

    # -----------------------------
    # 6) Peer tickers
    # -----------------------------
    peer_input = input("Optional: enter comma-separated peer tickers for industry comparison (or press Enter): ").strip()

    raw_peers = [p.strip() for p in peer_input.split(',')] if peer_input else []
    peers = []

    for p in raw_peers:
        try:
            resolved = resolver.resolve(p)
            peers.append(resolved)
        except Exception:
            print(f"Warning: could not resolve peer '{p}'. Skipping.")

    # -----------------------------
    # 7) Valuation (DCF + Multiples)
    # -----------------------------
    val = consolidate_valuation(
        info,
        fcf_now=fcf,
        forecast_growths=[0.08] * 5 if fcf else None,
        terminal_growth=0.02,
        wacc=None
    )

    peer_medians = peers_median(peers, ["PE", "PB", "EV/EBITDA"]) if peers else {}

    # -----------------------------
    # 8) Ratings
    # -----------------------------
    ratings = {
        "Revenue Growth": RatingEngine.rate_value(rev_growth, (0, 5)) if rev_growth is not None else "Data Unavailable",
        "Net Income Growth": RatingEngine.rate_value(ni_growth, (0, 5)) if ni_growth is not None else "Data Unavailable",
        "Operating Margin": RatingEngine.rate_value(op_margin * 100 if op_margin else None, (5, 15)),
        "ROIC": RatingEngine.rate_value(roic * 100 if roic else None, (8, 12)),
        "Debt/Equity": "Good" if info.get("debtToEquity") and info["debtToEquity"] < 100 else "Weak"
    }

    # Normalized 0–100 global score
    score = RatingEngine.compute_global_score(ratings)

    # -----------------------------
    # 9) Build final report
    # -----------------------------
    report = []
    report.append(f"\nFundamental & Valuation Report for {ticker}")
    report.append("=" * 60)

    report.append("\n-- Key Indicators --")
    report.append(f"Revenue growth (5y avg): {fmt_pct(rev_growth)}")
    report.append(f"Net income growth (5y avg): {fmt_pct(ni_growth)}")
    report.append(f"Operating margin: {fmt_pct(op_margin * 100) if op_margin else 'N/A'}")
    report.append(f"Net margin: {fmt_pct(net_margin * 100) if net_margin else 'N/A'}")
    report.append(f"ROE: {fmt_pct(roe * 100) if roe else 'N/A'}")
    report.append(f"ROA: {fmt_pct(roa * 100) if roa else 'N/A'}")
    report.append(f"ROIC (estimated): {fmt_pct(roic * 100) if roic else 'N/A'}")
    report.append(f"Debt/Equity: {fmt(info.get('debtToEquity'))}")
    report.append(f"Free Cash Flow (latest): {fmt(fcf)}")


    report.append("\n-- Ratings --")
    for k, v in ratings.items():
        report.append(f"{k}: {v}")

    report.append(f"\nGlobal Score: {score}/100")

    report.append("\n-- Valuation --")
    report.append(f"WACC used: {fmt_pct(val.get('wacc') * 100) if val.get('wacc') else 'N/A'}")
    for k, v in val.get("multiples", {}).items():
        report.append(f"{k}: {fmt(v)}")
    
    safe_fair, safe_entry = safe_intrinsic_price(info,
                                                val.get("intrinsic_price"),
                                                val.get("multiples", {}).get("fair_value"))

    report.append(f"Fair value (combined): {safe_fair}")
    report.append(f"Entry price (20% safety margin): {safe_entry}")
    report.append(f"Current market price: {info.get('currentPrice')}")


    if peers:
        report.append("\n-- Peer Medians --")
        report.append(json.dumps(peer_medians, indent=2))

    print("\n".join(report))


if __name__ == "__main__":
    run()
