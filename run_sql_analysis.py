"""Run every query in sql/analysis/ against the SQLite database and save each result as CSV.

Run:  python python/run_sql_analysis.py
"""
import sqlite3

import pandas as pd

from config import ANALYSIS_SQL_DIR, DB_PATH, TABLES


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    for path in sorted(ANALYSIS_SQL_DIR.glob("*.sql")):
        df = pd.read_sql_query(path.read_text(), con)
        out = TABLES / f"{path.stem}.csv"
        df.to_csv(out, index=False)
        print(f"{path.name:42s} -> {len(df):>4} rows  ({out.relative_to(out.parents[2])})")
    con.close()


if __name__ == "__main__":
    main()
