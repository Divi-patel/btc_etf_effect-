"""Project-level constants for the Table 7 rebuild."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
DOCS_DIR = PROJECT_ROOT / "docs"
TABLES_DIR = DOCS_DIR / "tables"

DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT")
DEFAULT_INTERVAL = "5m"
DEFAULT_START_MONTH = "2022-07"
DEFAULT_END_MONTH = "2024-10"


@dataclass(frozen=True)
class BreakDate:
    break_date: date
    label: str
    expected_pattern: str


BREAK_DATES = (
    BreakDate(
        date(2023, 8, 29),
        "Grayscale court ruling",
        "Weaker or less consistent than the baseline break",
    ),
    BreakDate(
        date(2023, 10, 23),
        "ETF enthusiasm / DTCC listing attention / Grayscale case closure",
        "Strongest jump-volatility decline and spillover shift",
    ),
    BreakDate(
        date(2024, 1, 10),
        "Official SEC spot Bitcoin ETF approval",
        "Weaker or less consistent than the baseline break",
    ),
)

