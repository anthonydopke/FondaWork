"""
Improved rating engine.
Encapsulates:
- Numeric threshold ratings
- Peer comparison
- Weighted global score
- Textual verdict
"""

from typing import Dict, Optional
import numpy as np


class RatingEngine:
    """Encapsulated rating evaluator with static utility methods."""

    SCORE_MAP = {
        "Good": 1.0,
        "Average": 0.5,
        "Weak": 0.0,
        "Data Unavailable": 0.0
    }

    @staticmethod
    def rate_value(value: Optional[float], thresholds: tuple) -> str:
        """Rate a numeric value according to thresholds (low, mid)."""
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return "Data Unavailable"

        try:
            v = float(value)
        except Exception:
            return "Data Unavailable"

        low, mid = thresholds
        if v >= mid:
            return "Good"
        elif v >= low:
            return "Average"
        return "Weak"

    @staticmethod
    def compare_to_peer(value: Optional[float], peer_median: Optional[float]) -> Optional[str]:
        """Compare company metric to median of its peers."""
        if value is None or peer_median is None:
            return None

        try:
            v = float(value)
            p = float(peer_median)
        except Exception:
            return None

        if p == 0:
            return None

        rel = (v - p) / p
        if rel <= -0.20:
            return "Below Peer"
        if rel >= 0.20:
            return "Above Peer"
        return "In line with peers"

    @classmethod
    def compute_global_score(cls, ratings: Dict[str, str], weights: Dict[str, float] = None) -> float:
        """Compute a weighted global score between 0 and 100."""
        if weights is None:
            weights = {k: 1.0 for k in ratings}

        total_weight = sum(weights.values())
        if total_weight == 0:
            return 0.0

        weighted = sum(cls.SCORE_MAP.get(r, 0.0) * weights.get(k, 1.0) for k, r in ratings.items())

        return round((weighted / total_weight) * 100, 2)

    @staticmethod
    def textual_verdict(score: float) -> str:
        """Text interpretation of the global weighted score."""
        if score >= 80:
            return "Strong fundamentals — attractive for long-term investors."
        if score >= 60:
            return "Decent fundamentals — consider further due diligence."
        if score >= 40:
            return "Mixed fundamentals — watch for risks."
        return "Weak fundamentals — risky for long-term investment."
