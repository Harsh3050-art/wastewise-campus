from services.db import get_conn
from services.bins import get_all_bins

BADGES = [(0, "Eco Starter"), (50, "Green Scout"), (150, "Upcycle Pro"), (400, "Campus Champion")]


def badge_info(points):
    idx = max(i for i, (need, _) in enumerate(BADGES) if points >= need)
    name = BADGES[idx][1]
    if idx + 1 < len(BADGES):
        lo, hi = BADGES[idx][0], BADGES[idx + 1][0]
        return name, BADGES[idx + 1][1], hi - points, (points - lo) / (hi - lo)
    return name, None, 0, 1.0


def user_stats(user_id):
    with get_conn() as conn:
        pts = conn.execute("SELECT total_points FROM users WHERE id = ?", (user_id,)).fetchone()[0]
        rank = conn.execute(
            "SELECT COUNT(*) + 1 FROM users WHERE role = 'student' AND total_points > ?",
            (pts,)).fetchone()[0]
        reports = conn.execute("SELECT COUNT(*) FROM reports WHERE user_id = ?", (user_id,)).fetchone()[0]
        ideas = conn.execute("SELECT COUNT(*) FROM adopted_ideas WHERE user_id = ?", (user_id,)).fetchone()[0]
        makes = conn.execute(
            "SELECT COUNT(*) FROM submissions WHERE user_id = ? AND status = 'approved'",
            (user_id,)).fetchone()[0]
    return {"points": pts, "rank": rank, "reports": reports, "ideas": ideas, "makes": makes}


def admin_kpis():
    df = get_all_bins()
    with get_conn() as conn:
        open_reports = conn.execute("SELECT COUNT(*) FROM reports WHERE status = 'open'").fetchone()[0]
        cleaned_today = conn.execute(
            "SELECT COUNT(*) FROM clean_log WHERE date(cleaned_at) = date('now')").fetchone()[0]
    k = {
        "total": len(df),
        "above80": int((df["fill_pct"] >= 80).sum()),
        "within6": int((df["hours_to_full"] <= 6).sum()),
        "avg_fill": float(df["fill_pct"].mean()) if len(df) else 0.0,
        "open_reports": open_reports,
        "cleaned_today": cleaned_today,
    }
    return df, k