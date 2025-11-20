# === logging_config.py ===
"""
Centralized logging configuration to be imported by modules.
"""

import logging


def setup_logging(level=logging.INFO):
    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    logging.basicConfig(level=level, format=fmt)
    # reduce verbosity of some noisy libs
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("yfinance").setLevel(logging.WARNING)

