"""
sector_profiles.py

Provides sector-aware analysis profiles for fundamental analysis.
API:
    from sector_profiles import SectorProfiles
    profile = SectorProfiles.get_profile(info_dict)

The returned profile is a dict with keys:
- sector: str
- metrics: Dict[str, bool]
- weights: Dict[str, float]    # weights sum is not strictly required but recommended
- preferred_multiples: List[str]
- thresholds: Dict[str, Tuple[float, float]]  # (low, mid) for RatingEngine.rate_value
- notes: Optional guidance strings
"""

from typing import Dict, Any, Tuple, List


class SectorProfiles:
    """Factory for sector-specific profiles used by the analysis pipeline."""

    # canonical sector buckets
    SECTOR_BUCKETS = {
        "BANKS": ["bank", "banks", "financial services", "banking"],
        "INSURANCE": ["insurance", "insurer", "reinsurance"],
        "LUXURY": ["apparel", "luxury", "cosmetics", "fashion", "leisure"],
        "TECH": ["technology", "software", "semiconductor", "internet", "tech"],
        "ENERGY": ["energy", "oil", "gas", "petroleum", "mining", "coal"],
        "UTILITIES": ["utilities", "electric", "power", "water", "gas distribution"],
        "HEALTHCARE": ["healthcare", "pharmaceutical", "biotech", "medical"],
        "REAL_ESTATE": ["real estate", "realestate", "property", "reits"],
        "CONSUMER": ["consumer staples", "consumer discretionary", "retail"],
        "INDUSTRIAL": ["industrial", "manufacturing", "capital goods"],
        "GENERAL": []  # fallback
    }

    @staticmethod
    def _normalize_text(v: Any) -> str:
        if not v:
            return ""
        try:
            return str(v).strip().lower()
        except Exception:
            return ""

    @classmethod
    def detect_sector_bucket(cls, info: Dict[str, Any]) -> str:
        """
        Attempt to map company info (info.get('sector'), info.get('industry'), shortName)
        to one of the canonical sector buckets.
        """
        # prefer explicit sector field from yfinance
        sector = cls._normalize_text(info.get("sector"))
        industry = cls._normalize_text(info.get("industry"))
        name = cls._normalize_text(info.get("shortName") or info.get("longName") or info.get("long_name") or "")

        probe = " ".join([sector, industry, name])

        for bucket, keywords in cls.SECTOR_BUCKETS.items():
            # empty keyword list means fallback
            if not keywords:
                continue
            for kw in keywords:
                if kw in probe:
                    return bucket

        # simple heuristics for common patterns
        if "financial" in probe or "bank" in probe or "bnp" in probe or "hsbc" in probe:
            return "BANKS"
        if "insur" in probe:
            return "INSURANCE"
        if "lvmh" in probe or "hermes" in probe or "lux" in probe:
            return "LUXURY"
        if "tech" in probe or "software" in probe or "semiconductor" in probe:
            return "TECH"
        if "oil" in probe or "gas" in probe or "energy" in probe or "petrol" in probe:
            return "ENERGY"
        if "utility" in probe or "power" in probe:
            return "UTILITIES"

        # fallback default
        return "GENERAL"

    @staticmethod
    def _base_profile() -> Dict[str, Any]:
        """Return a minimal, general-purpose profile used as fallback."""
        return {
            "sector": "GENERAL",
            "metrics": {
                "revenue_growth": True,
                "net_income_growth": True,
                "operating_margin": True,
                "net_margin": True,
                "roe": True,
                "roa": True,
                "roic": True,
                "fcf": True,
                "debt_to_equity": True,
                "gross_margin": False,
                "cet1_ratio": False,
            },
            "weights": {
                "revenue_growth": 0.20,
                "net_income_growth": 0.15,
                "operating_margin": 0.15,
                "roic": 0.15,
                "roe": 0.10,
                "fcf": 0.15,
                "debt_to_equity": 0.10,
            },
            "preferred_multiples": ["PE", "EV/EBITDA", "P/FCF"],
            "thresholds": {
                # (low, mid) thresholds for RatingEngine.rate_value
                "revenue_growth": (0, 5),
                "net_income_growth": (0, 5),
                "operating_margin": (5, 15),
                "roic": (8, 12),
                "roe": (8, 15),
                "fcf": (0, 5),
                "debt_to_equity": (0, 100),  # inverted logic may be applied elsewhere
            },
            "notes": "General fallback profile."
        }

    @classmethod
    def get_profile(cls, info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point. Returns a profile dict customized to the detected sector.
        """
        bucket = cls.detect_sector_bucket(info)
        profile = cls._base_profile()
        profile["sector"] = bucket

        # Now override by sector
        if bucket == "BANKS":
            profile.update({
                "metrics": {
                    "revenue_growth": False,
                    "net_income_growth": True,
                    "operating_margin": False,
                    "net_margin": True,
                    "roe": True,
                    "roa": True,
                    "roic": False,
                    "fcf": False,
                    "debt_to_equity": False,  # banks' capital structure behaves differently
                    "gross_margin": False,
                    "cet1_ratio": True,
                },
                "weights": {
                    "roe": 0.40,
                    "net_income_growth": 0.20,
                    "roa": 0.15,
                    "net_margin": 0.10,
                    "cet1_ratio": 0.15,
                },
                "preferred_multiples": ["PB", "PE"],
                "thresholds": {
                    "roe": (8, 12),
                    "net_income_growth": (0, 5),
                    "roa": (0.5, 1.5),
                    "net_margin": (5, 15),
                    "cet1_ratio": (8, 12),
                },
                "notes": "Banks: prefer P/B and capital adequacy metrics. Avoid ROIC and typical industrial multiples."
            })

        elif bucket == "INSURANCE":
            profile.update({
                "metrics": {
                    "revenue_growth": False,
                    "net_income_growth": True,
                    "operating_margin": False,
                    "net_margin": True,
                    "roe": True,
                    "roa": True,
                    "roic": False,
                    "fcf": False,
                    "debt_to_equity": False,
                    "gross_margin": False,
                    "cet1_ratio": False,
                },
                "weights": {
                    "roe": 0.35,
                    "net_income_growth": 0.25,
                    "net_margin": 0.20,
                    "roa": 0.20,
                },
                "preferred_multiples": ["PB", "PE"],
                "thresholds": {
                    "roe": (8, 12),
                    "net_income_growth": (0, 5),
                },
                "notes": "Insurance: focus on underwriting profitability and surplus adequacy (future enhancements)."
            })

        elif bucket == "LUXURY":
            profile.update({
                "metrics": {
                    "revenue_growth": True,
                    "net_income_growth": True,
                    "operating_margin": True,
                    "net_margin": True,
                    "roe": True,
                    "roa": True,
                    "roic": True,
                    "fcf": True,
                    "debt_to_equity": True,
                    "gross_margin": True,
                    "cet1_ratio": False,
                },
                "weights": {
                    "operating_margin": 0.30,
                    "revenue_growth": 0.25,
                    "roic": 0.20,
                    "fcf": 0.15,
                    "debt_to_equity": 0.10,
                },
                "preferred_multiples": ["PE", "EV/EBITDA", "P/S"],
                "thresholds": {
                    "operating_margin": (10, 20),
                    "revenue_growth": (2, 8),
                    "roic": (8, 12),
                    "fcf": (0, 5),
                },
                "notes": "Luxury & premium consumer brands: brand margins and ROIC are critical."
            })

        elif bucket == "TECH":
            profile.update({
                "metrics": {
                    "revenue_growth": True,
                    "net_income_growth": True,
                    "operating_margin": True,
                    "net_margin": True,
                    "roe": True,
                    "roa": True,
                    "roic": True,
                    "fcf": True,
                    "debt_to_equity": True,
                    "gross_margin": True,
                    "cet1_ratio": False,
                },
                "weights": {
                    "revenue_growth": 0.30,
                    "operating_margin": 0.20,
                    "fcf": 0.20,
                    "roic": 0.15,
                    "gross_margin": 0.15,
                },
                "preferred_multiples": ["P/FCF", "EV/Revenue", "EV/EBITDA"],
                "thresholds": {
                    "revenue_growth": (10, 25),
                    "operating_margin": (5, 15),
                    "fcf": (0, 5),
                    "roic": (5, 10),
                },
                "notes": "Tech: growth and FCF are primary; multiplicative valuation often uses EV/Revenue for unprofitable names."
            })

        elif bucket == "ENERGY":
            profile.update({
                "metrics": {
                    "revenue_growth": False,
                    "net_income_growth": True,
                    "operating_margin": True,
                    "net_margin": True,
                    "roe": True,
                    "roa": True,
                    "roic": True,
                    "fcf": True,
                    "debt_to_equity": True,
                    "gross_margin": False,
                    "cet1_ratio": False,
                },
                "weights": {
                    "fcf": 0.30,
                    "roic": 0.20,
                    "debt_to_equity": 0.20,
                    "operating_margin": 0.15,
                    "revenue_growth": 0.15,
                },
                "preferred_multiples": ["EV/EBITDA", "P/FCF"],
                "thresholds": {
                    "fcf": (0, 5),
                    "roic": (5, 10),
                    "debt_to_equity": (0, 3),  # for energy, lower is better but scale differs
                },
                "notes": "Energy: cyclical business—prefer cashflow and asset-backed valuation."
            })

        elif bucket == "UTILITIES":
            profile.update({
                "metrics": {
                    "revenue_growth": False,
                    "net_income_growth": True,
                    "operating_margin": True,
                    "net_margin": True,
                    "roe": True,
                    "roa": True,
                    "roic": True,
                    "fcf": True,
                    "debt_to_equity": True,
                    "gross_margin": False,
                    "cet1_ratio": False,
                },
                "weights": {
                    "fcf": 0.25,
                    "debt_to_equity": 0.25,
                    "roic": 0.20,
                    "net_income_growth": 0.15,
                    "roe": 0.15,
                },
                "preferred_multiples": ["EV/EBITDA", "P/FCF"],
                "thresholds": {
                    "debt_to_equity": (0, 150),
                    "fcf": (0, 5),
                },
                "notes": "Utilities: stability and leverage are key."
            })

        elif bucket == "HEALTHCARE":
            profile.update({
                "metrics": {
                    "revenue_growth": True,
                    "net_income_growth": True,
                    "operating_margin": True,
                    "net_margin": True,
                    "roe": True,
                    "roa": True,
                    "roic": True,
                    "fcf": True,
                    "debt_to_equity": True,
                    "gross_margin": True,
                    "cet1_ratio": False,
                },
                "weights": {
                    "revenue_growth": 0.25,
                    "roic": 0.20,
                    "operating_margin": 0.20,
                    "fcf": 0.20,
                    "debt_to_equity": 0.15,
                },
                "preferred_multiples": ["PE", "EV/EBITDA"],
                "thresholds": {
                    "revenue_growth": (5, 15),
                    "operating_margin": (5, 15),
                },
                "notes": "Healthcare: mix of defensive and growth depending on sub-sector."
            })

        elif bucket == "REAL_ESTATE":
            profile.update({
                "metrics": {
                    "revenue_growth": False,
                    "net_income_growth": True,
                    "operating_margin": False,
                    "net_margin": True,
                    "roe": True,
                    "roa": True,
                    "roic": False,
                    "fcf": True,
                    "debt_to_equity": True,
                    "gross_margin": False,
                    "cet1_ratio": False,
                },
                "weights": {
                    "fcf": 0.30,
                    "debt_to_equity": 0.30,
                    "roe": 0.20,
                    "net_income_growth": 0.20,
                },
                "preferred_multiples": ["P/FFO", "P/B", "EV/EBITDA"],
                "thresholds": {
                    "debt_to_equity": (50, 150),
                    "fcf": (0, 5),
                },
                "notes": "Real estate: financing structure and funds-from-operations matter."
            })

        elif bucket == "CONSUMER":
            # consumer staples / discretionary: use consumer/retail style weights
            profile.update({
                "metrics": {
                    "revenue_growth": True,
                    "net_income_growth": True,
                    "operating_margin": True,
                    "net_margin": True,
                    "roe": True,
                    "roa": True,
                    "roic": True,
                    "fcf": True,
                    "debt_to_equity": True,
                    "gross_margin": True,
                    "cet1_ratio": False,
                },
                "weights": {
                    "operating_margin": 0.25,
                    "revenue_growth": 0.25,
                    "roic": 0.20,
                    "fcf": 0.20,
                    "debt_to_equity": 0.10,
                },
                "preferred_multiples": ["PE", "EV/EBITDA", "P/S"],
                "thresholds": {
                    "operating_margin": (5, 15),
                    "revenue_growth": (0, 5),
                },
                "notes": "Consumer: margin and brand strength matter."
            })

        else:
            # GENERAL already set
            pass

        return profile
