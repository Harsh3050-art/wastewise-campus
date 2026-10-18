
from services.db import get_conn

with get_conn() as conn:
    print("Total readings:",
          conn.execute("SELECT COUNT(*) FROM bin_readings").fetchone()[0])

    print("Earliest reading:",
          conn.execute("SELECT MIN(recorded_at) FROM bin_readings").fetchone()[0])

    print("Latest reading:",
          conn.execute("SELECT MAX(recorded_at) FROM bin_readings").fetchone()[0])

    print("Sample readings:")
    for row in conn.execute(
        "SELECT bin_id, fill_pct, recorded_at "
        "FROM bin_readings ORDER BY recorded_at DESC LIMIT 5"
    ):
        print(tuple(row))
