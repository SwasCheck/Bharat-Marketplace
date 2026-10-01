"""Run the whole pipeline end to end (works on Windows, macOS and Linux).

    python run_pipeline.py

Steps: generate data -> build SQLite database -> run SQL analysis -> statistics and charts -> Power BI export.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STEPS = [
    "generate_data.py",
    "load_db.py",
    "run_sql_analysis.py",
    "analysis.py",
    "export_powerbi.py",
]

for step in STEPS:
    print(f"\n=== {step} ===")
    subprocess.run([sys.executable, str(ROOT / "python" / step)], check=True, cwd=ROOT / "python")
print("\nDone. Open the Power BI files in /powerbi and the CSVs in /data/processed.")
