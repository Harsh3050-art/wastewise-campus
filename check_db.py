
from services.db import get_conn

with get_conn() as conn:

    # 1. Check table record counts
    for t in [
        "users", "bins", "reports", "report_votes",
        "follows", "clean_log", "notifications",
        "points_log", "submissions"
    ]:
        count = conn.execute(
            f"SELECT COUNT(*) FROM {t}"
        ).fetchone()[0]
        print(t, count)

    # 2. Check bins by type
    print("\nBins by type:")
    print([
        tuple(r) for r in conn.execute(
            "SELECT type, COUNT(*) FROM bins GROUP BY type"
        )
    ])

    # 3. Check fill-level ranges by usage
    print("\nFill ranges by usage:")
    print([
        tuple(r) for r in conn.execute(
            """
            SELECT usage, ROUND(MIN(fill_pct)),
                   ROUND(MAX(fill_pct))
            FROM bins
            GROUP BY usage
            """
        )
    ])

    # 4. Check registered users and password hashes
    print("\nRegistered users:")
    print([
        tuple(r) for r in conn.execute(
            """
            SELECT id, name, identifier, role,
                   substr(password_hash, 1, 7)
            FROM users
            """
        )
    ])
