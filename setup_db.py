
import random
import sys
import pandas as pd
from services.db import init_db, get_conn

RATE = {
    "low": 1.0,
    "medium": 2.0,
    "high": 3.5,
    "very high": 5.0,
}

FILL = {
    "low": (5, 30),
    "medium": (15, 50),
    "high": (35, 75),
    "very high": (55, 92),
}

RESET_FILL = "--reset-fill" in sys.argv

init_db()
df = pd.read_csv("data/bins.csv")
random.seed(42)

with get_conn() as conn:
    for _, r in df.iterrows():
        lo, hi = FILL[r["usage"]]
        fill = round(random.uniform(lo, hi), 1)

        conn.execute(
            """
            INSERT INTO bins (
                bin_id, name, lat, lng, type, size,
                capacity_litres, usage, fill_pct,
                fill_rate_per_hr
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(bin_id) DO UPDATE SET
                name = excluded.name,
                lat = excluded.lat,
                lng = excluded.lng,
                type = excluded.type,
                size = excluded.size,
                capacity_litres = excluded.capacity_litres,
                usage = excluded.usage
            """,
            (
                r["bin_id"], r["name"], r["lat"], r["lng"],
                r["type"], r["size"], int(r["capacity_litres"]),
                r["usage"], fill, RATE[r["usage"]]
            ),
        )

        if RESET_FILL:
            conn.execute(
                """
                UPDATE bins
                SET fill_pct = ?, fill_rate_per_hr = ?
                WHERE bin_id = ?
                """,
                (fill, RATE[r["usage"]], r["bin_id"]),
            )

print("Database ready with", len(df), "bins")
