"""Shared paths, constants and the chart palette used by every script."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
DB_PATH = ROOT / "data" / "marketplace.db"
SQL_DIR = ROOT / "sql"
ANALYSIS_SQL_DIR = SQL_DIR / "analysis"
TABLES = ROOT / "reports" / "tables"
FIGURES = ROOT / "reports" / "figures"

SEED = 42
START_DATE = "2025-01-01"
END_DATE = "2025-12-31"

# Plum / magenta palette used in charts and the Power BI theme.
PLUM = "#570D48"
MAGENTA = "#9F2089"
PINK = "#F43397"
TEAL = "#1F6F8B"
GREY = "#6A4A61"
LIGHT = "#F8E9F3"
GOOD = "#1C7F54"
BAD = "#B83636"
