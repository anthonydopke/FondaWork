# === streamlit_app.py ===
"""
Streamlit frontend for non-technical users.
Run with: streamlit run streamlit_app.py
"""

import streamlit as st

from data_fetcher import DataFetcher
from growth import compute_revenue_growth, compute_net_income_growth
from profitability import compute_roic, compute_operating_margin, compute_net_margin
from valuation import consolidate_valuation
from industry import peers_median
from rating_engine import RatingEngine, compute_global_score, textual_verdict
from logging_config import setup_logging

setup_logging()

# --- Streamlit Setup ---
st.set_page_config(page_title='FondaWork', layout='centered')
st.title('FondaWork — Fundamental & Valuation Analyzer')

st.markdown('Enter a company name (e.g. LVMH) or ticker (MC.PA, AAPL)')
company = st.text_input('Company name or ticker', value='LVMH')
peers_input = st.text_input('Optional: comma-separated peer tickers', value='')

# -------------------------------------------------
#                   MAIN ACTION
# -------------------------------------------------
if st.button('Run Analysis'):
    ticker = company.strip()
    df = DataFetcher(ticker)

    # 1️⃣ Validate ticker
    if not df.validate_ticker():
        st.error('Ticker not valid or no market data available.')
        st.stop()

    # 2️⃣ Fetch raw data
    info = df.get_info()
    income = df.get_income()
    balance = df.get_balance()
    cash = df.get_cashflow()

    # 3️⃣ Compute fundamentals
    rev_g = compute_revenue_growth(income)
    ni_g = compute_net_income_growth(income)
    roic = compute_roic(income, balance, info)
    opm = compute_operating_margin(info)
    netm = compute_net_margin(info)

    # 4️⃣ Compute FCF
    fcf = None
    if not cash.empty:
        # Common FCF column names
        for col in ["Free Cash Flow", "freeCashflow", "Free Cash Flow (TTM)"]:
            if col in cash.columns and not cash[col].dropna().empty:
                fcf = float(cash[col].dropna().iloc[-1])
                break

    # Fallback FCF calculation
    if fcf is None:
        try:
            cfo = cash[[c for c in cash.columns if 'Operating' in c or 'operating' in c][0]].dropna().iloc[-1]
            capex = cash[[c for c in cash.columns if 'Capital' in c or 'Capex' in c][0]].dropna().iloc[-1]
            fcf = float(cfo) - float(capex)
        except Exception:
            fcf = None

    # 5️⃣ Valuation
    val = consolidate_valuation(
        info,
        fcf_now=fcf,
        forecast_growths=[0.06] * 5  # simple default 6% growth
    )

    # 6️⃣ Peer multiples
    peers = [p.strip() for p in peers_input.split(',')] if peers_input else []
    peer_medians = peers_median(peers, ['PE', 'PB', 'EV/EBITDA']) if peers else {}

    # 7️⃣ Ratings
    ratings = {
        'Revenue Growth': RatingEngine.rate_value(rev_g, (0, 5)) if rev_g else 'Data Unavailable',
        'Net Income Growth': RatingEngine.rate_value(ni_g, (0, 5)) if ni_g else 'Data Unavailable',
        'Operating Margin': RatingEngine.rate_value(opm*100 if opm else None, (5, 15)),
        'ROIC': RatingEngine.rate_value(roic*100 if roic else None, (8, 12))
    }

    score = RatingEngine.compute_global_score(ratings)

    # -----------------------------------------
    #               DISPLAY
    # -----------------------------------------
    st.subheader('Key Figures')
    st.write('Current price:', info.get('currentPrice'))
    st.write('Market cap:', info.get('marketCap'))
    st.write('Revenue growth (5y avg):', rev_g)
    st.write('ROIC (est):', roic)
    st.write('Operating margin:', opm)

    st.subheader('Valuation')
    st.write('WACC used:', val.get('wacc'))
    st.write('Multiples:', val.get('multiples'))
    st.write('Intrinsic price:', val.get('intrinsic_price'))
    st.write('Suggested buy price (20% MOS):', val.get('suggested_buy_price'))

    if peers:
        st.subheader('Peer medians')
        st.json(peer_medians)

    st.subheader('Ratings & Verdict')
    st.json(ratings)
    st.write('Global score:', score)
    st.info(textual_verdict(score))
