# app.py
"""
Streamlit frontend for FondaWork — updated safe valuation & UI formatting.
Run with: streamlit run streamlit_app.py
"""

import streamlit as st
from typing import Tuple, Optional

from data_fetcher import DataFetcher
from growth import compute_revenue_growth, compute_net_income_growth
from profitability import compute_roic, compute_operating_margin, compute_net_margin
from valuation import consolidate_valuation
from industry import peers_median
from rating_engine import RatingEngine
from logging_config import setup_logging
from ticker_resolver import TickerResolver

# optionally import safe_intrinsic_price if present in valuation.py
try:
    from valuation import safe_intrinsic_price
except Exception:
    safe_intrinsic_price = None  # we'll use a fallback

setup_logging()

# --- Streamlit Setup ---
st.set_page_config(page_title='FondaWork', layout='centered')
st.title('FondaWork — Fundamental & Valuation Analyzer')

st.markdown('Enter a company name (e.g. LVMH) or ticker (MC.PA, AAPL)')
company = st.text_input('Company name or ticker', value='LVMH')
peers_input = st.text_input('Optional: comma-separated peer tickers', value='')

# -------------------------
# Helpers
# -------------------------
def fmt(x) -> str:
    try:
        return f"{float(x):,.2f}"
    except Exception:
        return "N/A"

def fmt_pct_from_decimal(x) -> str:
    try:
        return f"{float(x)*100:.2f}%"
    except Exception:
        return "N/A"

def fmt_pct_direct(x) -> str:
    try:
        return f"{float(x):.2f}%"
    except Exception:
        return "N/A"

def compute_multiples_fair_price(info: dict, peer_medians: dict, multiples: dict) -> Optional[float]:
    """
    Heuristic to derive a multiples-based 'fair price' using peer medians.
    Priority:
    1) If peer median PE and trailingEps available -> price = peer_PE * EPS
    2) Else if company PE & peer_PE -> price = currentPrice * (peer_PE / company_PE)
    3) Else if EV/EBITDA peer median and company EV/EBITDA available -> scale market cap
    Otherwise None.
    """
    current_price = info.get("currentPrice")
    trailing_eps = info.get("trailingEps")
    company_pe = multiples.get("PE")
    company_ev_ebitda = multiples.get("EV/EBITDA")
    market_cap = info.get("marketCap")

    peer_pe = peer_medians.get("PE")
    peer_ev_ebitda = peer_medians.get("EV/EBITDA")

    # 1) peer PE * EPS
    if peer_pe and trailing_eps:
        try:
            return float(peer_pe) * float(trailing_eps)
        except Exception:
            pass

    # 2) scale current price by peer/company PE ratio
    if company_pe and peer_pe and current_price:
        try:
            return float(current_price) * (float(peer_pe) / float(company_pe))
        except Exception:
            pass

    # 3) EV/EBITDA scaling -> approximate price via market cap scaling
    if company_ev_ebitda and peer_ev_ebitda and market_cap:
        try:
            scaling = float(peer_ev_ebitda) / float(company_ev_ebitda)
            return float(market_cap) * scaling / float(info.get("sharesOutstanding", 1))
        except Exception:
            pass

    return None

# -------------------------
# Main action
# -------------------------
if st.button('Run Analysis'):
    resolver = TickerResolver()
    ticker_input = company.strip()
    ticker = resolver.resolve(ticker_input)
    st.write("Resolved ticker:", ticker)

    df = DataFetcher(ticker)
    if not df.validate_ticker():
        st.error('Ticker not valid or no market data available.')
        st.stop()

    info = df.get_info()
    income = df.get_income()
    balance = df.get_balance()
    cash = df.get_cashflow()

    # Fundamentals
    rev_g = compute_revenue_growth(income)
    ni_g = compute_net_income_growth(income)
    roic = compute_roic(income, balance, info)
    opm = compute_operating_margin(info)
    netm = compute_net_margin(info)

    # Compute FCF (best-effort)
    fcf = None
    if not cash.empty:
        for col in ["Free Cash Flow", "freeCashflow", "Free Cash Flow (TTM)"]:
            if col in cash.columns and not cash[col].dropna().empty:
                try:
                    fcf = float(cash[col].dropna().iloc[-1])
                except Exception:
                    fcf = None
                break

    if fcf is None:
        try:
            cfo_candidates = [c for c in cash.columns if 'Operating' in c or 'operating' in c]
            capex_candidates = [c for c in cash.columns if 'Capital' in c or 'Capex' in c]
            if cfo_candidates and capex_candidates:
                cfo = float(cash[cfo_candidates[0]].dropna().iloc[-1])
                capex = float(cash[capex_candidates[0]].dropna().iloc[-1])
                fcf = cfo - capex
        except Exception:
            fcf = None

    # Resolve peers safely
    raw_peers = [p.strip() for p in peers_input.split(',')] if peers_input else []
    resolved_peers = []
    for p in raw_peers:
        if not p:
            continue
        try:
            r = resolver.resolve(p)
            resolved_peers.append(r)
        except Exception:
            st.warning(f"Could not resolve peer '{p}'. Skipping.")

    # Valuation (DCF + multiples)
    val = consolidate_valuation(
        info,
        fcf_now=fcf,
        forecast_growths=[0.06] * 5 if fcf else None
    )

    # Peer medians (only resolved tickers)
    peer_medians = peers_median(resolved_peers, ['PE', 'PB', 'EV/EBITDA']) if resolved_peers else {}

    # Compute a multiples-derived fair price (best-effort)
    multiples = val.get("multiples", {}) if val else {}
    multiples_fair = compute_multiples_fair_price(info, peer_medians, multiples)

    # Compute safe blended fair value using safe_intrinsic_price if available
    if safe_intrinsic_price:
        fair_value, entry_price = safe_intrinsic_price(info, val.get('intrinsic_price'), multiples_fair)
    else:
        # Fallback: simple weighted blend and sanity checks (duplicate of safe_intrinsic_price logic)
        current = info.get("currentPrice")
        dcf_price = val.get('intrinsic_price') if val else None
        values = []
        if multiples_fair:
            values.append(multiples_fair * 0.6)
        if dcf_price:
            values.append(dcf_price * 0.4)
        if values:
            fair_value = sum(values)
            if current:
                if fair_value > current * 2:
                    fair_value = (fair_value + current * 2) / 2
                if fair_value < current * 0.3:
                    fair_value = max(fair_value, current * 0.3)
            entry_price = round(fair_value * 0.8, 2)
            fair_value = round(fair_value, 2)
        else:
            fair_value, entry_price = None, None

    # Ratings and scoring
    ratings = {
        'Revenue Growth': RatingEngine.rate_value(rev_g, (0, 5)) if rev_g else 'Data Unavailable',
        'Net Income Growth': RatingEngine.rate_value(ni_g, (0, 5)) if ni_g else 'Data Unavailable',
        'Operating Margin': RatingEngine.rate_value(opm*100 if opm else None, (5, 15)),
        'ROIC': RatingEngine.rate_value(roic*100 if roic else None, (8, 12))
    }
    score = RatingEngine.compute_global_score(ratings)

    # -------------------------
    # Display
    # -------------------------
    st.subheader('Key Figures')
    st.write('Current price:', fmt(info.get('currentPrice')))
    st.write('Market cap:', fmt(info.get('marketCap')))
    st.write('Revenue growth (5y avg):', fmt_pct_from_decimal(rev_g))
    st.write('ROIC (est):', fmt_pct_from_decimal(roic) if roic else 'N/A')
    st.write('Operating margin:', fmt_pct_from_decimal(opm) if opm else 'N/A')

    st.subheader('Valuation (Safe Model)')
    st.write('WACC used:', fmt_pct_from_decimal(val.get('wacc')) if val.get('wacc') else 'N/A')
    st.write('Multiples (raw):', {k: fmt(v) for k, v in (multiples or {}).items()})

    st.write('Fair value (blended):', fmt(fair_value) if fair_value else 'N/A')
    st.write('Entry price (20% safety margin):', fmt(entry_price) if entry_price else 'N/A')
    st.write('Current market price:', fmt(info.get('currentPrice')))

    # Valuation verdict
    if fair_value and info.get('currentPrice') is not None:
        cur = float(info.get('currentPrice'))
        if cur < entry_price:
            st.success("📉 Undervalued — price is below the suggested entry price")
        elif cur <= fair_value:
            st.info("⚖️ Fairly valued — price is between entry and fair value")
        else:
            st.error("📈 Overvalued — price is above the fair value")

    if resolved_peers:
        st.subheader('Peer medians (resolved)')
        st.json(peer_medians)

    st.subheader('Ratings & Verdict')
    st.json(ratings)
    st.write('Global score:', f"{score:.2f} / 100")
    st.info(RatingEngine.textual_verdict(score))
