
from services.db import get_conn


def award_in(conn, user_id, points, reason, ref_id=None, max_per_day=None):
    """Add points inside an open connection. Returns points actually given."""
    if max_per_day is not None:
        n = conn.execute(
            "SELECT COUNT(*) FROM points_log WHERE user_id = ? AND reason = ? "
            "AND points > 0 AND date(created_at) = date('now')",
            (user_id, reason),
        ).fetchone()[0]

        if n >= max_per_day:
            return 0

    conn.execute(
        "INSERT INTO points_log (user_id, points, reason, ref_id) VALUES (?,?,?,?)",
        (user_id, points, reason, ref_id),
    )
    conn.execute(
        "UPDATE users SET total_points = total_points + ? WHERE id = ?",
        (points, user_id),
    )
    return points


def award(user_id, points, reason, ref_id=None, max_per_day=None):
    with get_conn() as conn:
        return award_in(conn, user_id, points, reason, ref_id, max_per_day)
