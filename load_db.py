"""Create the SQLite database from sql/00_schema.sql and load the raw CSVs.

Run:  python python/load_db.py
"""
import sqlite3

import pandas as pd

from config import DB_PATH, END_DATE, RAW, SQL_DIR, START_DATE

FESTIVE_MONTHS = {10, 11}  # Navratri / Diwali season


def build_dim_date() -> pd.DataFrame:
    dates = pd.date_range(START_DATE, END_DATE, freq="D")
    return pd.DataFrame({
        "date_key": dates.strftime("%Y-%m-%d"),
        "year": dates.year,
        "month": dates.month,
        "month_start": dates.to_period("M").to_timestamp().strftime("%Y-%m-%d"),
        "month_name": dates.strftime("%b"),
        "week_of_year": dates.isocalendar().week.astype(int).to_numpy(),
        "day_of_week": dates.dayofweek,
        "is_weekend": (dates.dayofweek >= 5).astype(int),
        "is_festive": dates.month.isin(FESTIVE_MONTHS).astype(int),
    })


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript((SQL_DIR / "00_schema.sql").read_text())

    build_dim_date().to_sql("dim_date", con, if_exists="append", index=False)
    for name in ["dim_city", "dim_category", "dim_customer", "dim_seller", "fact_orders"]:
        df = pd.read_csv(RAW / f"{name}.csv")
        df.to_sql(name, con, if_exists="append", index=False)

    con.commit()
    for t in ["dim_city", "dim_category", "dim_customer", "dim_seller", "dim_date", "fact_orders"]:
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t:14s} {n:>9,} rows")
    bad = con.execute("PRAGMA foreign_key_check").fetchall()
    print("foreign key violations:", len(bad))
    con.close()


if __name__ == "__main__":
    main()
