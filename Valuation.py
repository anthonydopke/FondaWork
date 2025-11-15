"""
Module: valuation
Provides functions to compute simple stock valuation and suggest entry points.
Integrates with yfinance info dictionary.
"""

def simple_valuation(info, growth_rate=0.10):
    """
    info: dict from yfinance
    growth_rate: expected annual EPS growth for PEG calculation (default 10%)

    Returns a dict with ratio valuations and suggested entry points.
    """

    price = info.get("currentPrice")
    eps = info.get("trailingEps")
    pe_ratio = info.get("trailingPE")
    book_value = info.get("bookValue")
    pb_ratio = info.get("priceToBook")
    fcf = info.get("freeCashflow")
    shares_outstanding = info.get("sharesOutstanding")

    # Compute P/FCF if data available
    pfcf = None
    if fcf and shares_outstanding:
        fcf_per_share = fcf / shares_outstanding
        pfcf = price / fcf_per_share if fcf_per_share != 0 else None

    # PEG calculation
    peg = None
    if pe_ratio and growth_rate:
        peg = pe_ratio / (growth_rate*100)

    # Valuation heuristics
    valuation = {}
    if pe_ratio:
        valuation["PER"] = "Undervalued" if pe_ratio < 15 else ("Fair" if pe_ratio < 25 else "Overvalued")
    if pb_ratio:
        valuation["P/B"] = "Undervalued" if pb_ratio < 1 else ("Fair" if pb_ratio < 3 else "Overvalued")
    if peg:
        valuation["PEG"] = "Undervalued" if peg < 1 else ("Fair" if peg < 1.5 else "Overvalued")
    if pfcf:
        valuation["P/FCF"] = "Undervalued" if pfcf < 15 else ("Fair" if pfcf < 25 else "Overvalued")

    # Suggested entry point: 10% below current price if undervalued
    suggested_entry = None
    if price:
        undervalued_ratios = [v for v in valuation.values() if v == "Undervalued"]
        if undervalued_ratios:
            suggested_entry = round(price * 0.90, 2)  # 10% discount as a rough guide
        else:
            suggested_entry = round(price, 2)  # fair or overvalued → current price

    return {
        "valuation_ratios": valuation,
        "current_price": price,
        "suggested_entry": suggested_entry
    }
