
from services.db import get_conn

with get_conn() as conn:
    tables = [
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    ]

    print("report_votes exists:", "report_votes" in tables)
    print("Tables:", tables)
