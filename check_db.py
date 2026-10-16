
from services.db import get_conn

with get_conn() as conn:
    for t in [
        "users", "bins", "reports",
        "notifications", "points_log", "submissions"
    ]:
        count = conn.execute(
            f"SELECT COUNT(*) FROM {t}"
        ).fetchone()[0]
        print(t, count)

    print(
        [tuple(r) for r in conn.execute(
            "SELECT type, COUNT(*) FROM bins GROUP BY type"
        )]
    )

    print(
        [tuple(r) for r in conn.execute(
            """
            SELECT usage, ROUND(MIN(fill_pct)),
                   ROUND(MAX(fill_pct))
            FROM bins
            GROUP BY usage
            """
        )]
    )

    print(
        [tuple(r) for r in conn.execute(
            """
            SELECT id, name, identifier, role,
                   substr(password_hash, 1, 7)
            FROM users
            """
        )]
    )
