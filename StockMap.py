"""
Module: stock_map
Provides a manually curated map of common stock names to Yahoo Finance tickers.
Falls back to Yahoo Finance's unofficial autocomplete API when no match is found.
Comments and method names are in English.
"""

import requests

STOCK_MAP = {
    # --- France (CAC40) ---
    "lvmh": "MC.PA",
    "air liquide": "AI.PA",
    "loreal": "OR.PA",
    "hermes": "RMS.PA",
    "total": "TTE.PA",
    "danone": "BN.PA",
    "bnp paribas": "BNP.PA",
    "safran": "SAF.PA",
    "stellantis": "STLAM.MI",
    "carrefour": "CA.PA",
    "engie": "ENGI.PA",
    "pernod ricard": "RI.PA",
    "capgemini": "CAP.PA",
    "vinci": "DG.PA",
    "saint gobain": "SGO.PA",
    "essilorluxottica": "EL.PA",

    # --- US Large Caps ---
    "apple": "AAPL",
    "microsoft": "MSFT",
    "amazon": "AMZN",
    "tesla": "TSLA",
    "meta": "META",
    "google": "GOOG",
    "alphabet": "GOOG",
    "nvidia": "NVDA",
    "netflix": "NFLX",
    "amd": "AMD",
    "intel": "INTC",
}


def yahoo_autocomplete_search(query: str) -> str | None:
    """
    Uses Yahoo Finance's unofficial autocomplete API to resolve a company
    name into a ticker. Returns the first match or None if nothing found.
    """

    try:
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={query}"
        resp = requests.get(url, timeout=5)
        data = resp.json()

        quotes = data.get("quotes", [])
        if quotes:
            return quotes[0].get("symbol")
    except Exception:
        pass

    return None


def resolve_ticker(user_input: str) -> str:
    """
    Resolve a stock name into a Yahoo Finance ticker.

    Resolution order:
    1. Clean the input
    2. Try the internal map
    3. Try Yahoo's autocomplete API
    4. Fallback: assume the user input is already the ticker
    """

    clean = user_input.strip().lower()

    # Step 1 — direct map
    if clean in STOCK_MAP:
        return STOCK_MAP[clean]

    # Step 2 — Yahoo Finance autocomplete API
    yahoo_result = yahoo_autocomplete_search(clean)
    if yahoo_result:
        return yahoo_result.upper()

    # Step 3 — fallback
    return user_input.strip().upper()
