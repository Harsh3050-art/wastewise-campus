from services.db import get_conn

REASON_LABEL = {
    "report_confirmed": "Bin report confirmed",
    "idea_adopted": "Reuse idea tried",
    "creation_approved": "Creation approved",
    "creation_fake": "Penalty: creation rejected as fake",
    "creation_revoked": "Approval withdrawn after review",
}


def get_profile(user_id):
    with get_conn() as conn:
        r = conn.execute("SELECT id, name, identifier, role, hostel_or_dept, created_at "
                         "FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(r) if r else None


def my_reports(user_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT r.id, b.name AS bin_name, r.tag, r.status, r.created_at "
            "FROM reports r JOIN bins b ON b.bin_id = r.bin_id "
            "WHERE r.user_id = ? ORDER BY r.id DESC LIMIT 50", (user_id,)).fetchall()
    return [dict(r) for r in rows]


def points_history(user_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT created_at, points, reason FROM points_log WHERE user_id = ? "
            "ORDER BY id DESC LIMIT 100", (user_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["reason"] = REASON_LABEL.get(d["reason"], d["reason"])
        out.append(d)
    return out


def update_group(user_id, value):
    with get_conn() as conn:
        conn.execute("UPDATE users SET hostel_or_dept = ? WHERE id = ?",
                     ((value or "").strip()[:60], user_id))