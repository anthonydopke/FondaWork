# ==============================================
# === rating_engine.py
# ==============================================

"""
Module: rating_engine
Assigns qualitative ratings (Good / Average / Weak) based on computed indicators.
"""

class RatingEngine:
    """Produces qualitative ratings for all fundamental indicators."""

    @staticmethod
    def rate_value(value, thresholds):
        """Rate a numeric value according to (low, medium) thresholds."""
        if value is None:
            return "Data Unavailable"
        if value < thresholds[0]:
            return "Weak"
        elif value < thresholds[1]:
            return "Average"
        else:
            return "Good"

    @staticmethod
    def compute_global_score(ratings: dict):
        """Compute a global score out of 6 based on 'Good' ratings."""
        return sum(1 for r in ratings.values() if r == "Good")


