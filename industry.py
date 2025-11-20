# industry.py
"""
Simple helper to compute industry/peer medians for multiples.
You must provide a list of peer tickers (strings). This module will fetch `info` for each peer
(using yfinance) and compute medians for the requested multiple keys.
"""

import yfinance as yf
from typing import List, Dict
import numpy as np


def peers_median(peers: List[str], keys: List[str]) -> Dict[str, float]:
    """
    peers: list of tickers, keys: list of multiple keys e.g. ["PE", "PB", "EV/EBITDA"]
    Returns dict key->median (None if cannot compute).
    """
    results = {k: [] for k in keys}
    for t in peers:
        try:
            asset = yf.Ticker(t)
            info = asset.info or {}
            # map keys to info fields
            mapping = {
                "PE": info.get("trailingPE") or info.get("forwardPE"),
                "PB": info.get("priceToBook"),
                "PS": info.get("priceToSalesTrailing12Months"),
                "EV/EBITDA": None
            }
            # compute EV/EBITDA
            market_cap = info.get("marketCap")
            total_debt = info.get("totalDebt") or 0
            cash = info.get("totalCash") or 0
            ebitda = info.get("ebitda")
            if market_cap and ebitda and ebitda != 0:
                mapping["EV/EBITDA"] = (market_cap + (total_debt or 0) - (cash or 0)) / ebitda
            for k in keys:
                v = mapping.get(k)
                if v is not None:
                    try:
                        results[k].append(float(v))
                    except Exception:
                        pass
        except Exception:
            pass
    medians = {}
    for k, arr in results.items():
        if arr:
            medians[k] = float(np.median(arr))
        else:
            medians[k] = None
    return medians
