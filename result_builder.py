# ==============================================
# === result_builder.py
# ==============================================

"""
Module: result_builder
Formats the final output for the user (text, JSON, HTML, etc.).
"""

class ResultBuilder:
    """Builds readable results for frontend or terminal display."""

    def build_text_report(self, ticker: str, indicators: dict, ratings: dict, score: int) -> str:
        """Return a fully formatted fundamental analysis text report."""
        report = [
            f"Fundamental Analysis Report for {ticker}",
            "==========================================",
            "",
            "--- Raw Indicators ---",
        ]

        for key, val in indicators.items():
            report.append(f"{key}: {val}")

        report.append("\n--- Ratings ---")
        for key, val in ratings.items():
            report.append(f"{key}: {val}")

        report.append("\n-- Global Rating --")
        report.append(f"Score: {score:.1f} / 100")

        if score >= 5:
            report.append("Verdict: High‑quality company with strong long‑term outlook.")
        elif score >= 3:
            report.append("Verdict: Decent company but some weaknesses to watch.")
        else:
            report.append("Verdict: Weak fundamentals, high long‑term risk.")

        return "\n".join(report)


