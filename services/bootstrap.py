"""Make sure the database, bins and forecast model exist (first start, or a fresh deploy)."""
from pathlib import Path

import pandas as pd

from services.db import get_conn, init_db

ROOT = Path(__file__).resolve().parent.parent
RATE = {"low": 1.0, "medium": 2.0, "high": 3.5, "very high": 5.0}


def load_bins_from_csv():
    df = pd.read_csv(ROOT / "data" / "bins.csv")
    with get_conn() as conn:
        for _, r in df.iterrows():
            conn.execute(
                "INSERT OR IGNORE INTO bins (bin_id, name, lat, lng, type, size, capacity_litres, "
                "usage, fill_pct, fill_rate_per_hr) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (r["bin_id"], r["name"], r["lat"], r["lng"], r["type"], r["size"],
                 int(r["capacity_litres"]), r["usage"], 20.0, RATE[r["usage"]]))
    return len(df)


def ensure_ready():
    init_db()
    with get_conn() as conn:
        n_bins = conn.execute("SELECT COUNT(*) FROM bins").fetchone()[0]
    if n_bins == 0:
        print("First start: loading bins and building 28 days of simulated history...")
        load_bins_from_csv()
        from ml.simulator import backfill
        backfill(28)
    from ml.forecast import MODEL_PATH, train
    if not MODEL_PATH.exists():
        train()