from datetime import datetime

import pandas as pd

from services.db import get_conn
from services.notifications import add_in
from services.points import award_in
from services.timeutil import local_str

REPORT_POINTS = 5
REPORT_DAILY_CAP = 5
TS = "%Y-%m-%d %H:%M:%S"


def mark_cleaned(bin_ids, admin_id, reports_valid=True):
    summary = {"bins": 0, "reports": 0, "notified": 0, "points": 0}
    now_local = datetime.now().strftime(TS)
    with get_conn() as conn:
        for bid in bin_ids:
            b = conn.execute("SELECT name, fill_pct FROM bins WHERE bin_id = ? AND active = 1",
                             (bid,)).fetchone()
            if not b:
                continue
            name = b["name"]
            conn.execute("UPDATE bins SET fill_pct = 0, last_cleaned_at = ? WHERE bin_id = ?",
                         (now_local, bid))
            conn.execute("INSERT INTO clean_log (bin_id, admin_id, fill_before) VALUES (?,?,?)",
                         (bid, admin_id, b["fill_pct"]))
            conn.execute(
                "INSERT INTO bin_readings (bin_id, fill_pct, recorded_at) "
                "SELECT ?, 0, COALESCE(datetime(MAX(recorded_at), '+1 second'), "
                "datetime('now', 'localtime')) FROM bin_readings WHERE bin_id = ?", (bid, bid))

            reps = conn.execute("SELECT id, user_id FROM reports WHERE bin_id = ? AND status = 'open'",
                                (bid,)).fetchall()
            conn.execute("UPDATE reports SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP "
                         "WHERE bin_id = ? AND status = 'open'", (bid,))
            reporters = {r["user_id"] for r in reps}
            voters = set()
            if reps:
                q = ",".join("?" * len(reps))
                voters = {row[0] for row in conn.execute(
                    f"SELECT DISTINCT user_id FROM report_votes WHERE report_id IN ({q})",
                    [r["id"] for r in reps])}
            followers = {row[0] for row in conn.execute(
                "SELECT user_id FROM follows WHERE bin_id = ?", (bid,))}

            for r in reps:
                if reports_valid:
                    pts = award_in(conn, r["user_id"], REPORT_POINTS, "report_confirmed",
                                   f"report:{r['id']}", max_per_day=REPORT_DAILY_CAP)
                    if pts:
                        msg = (f"Your report on {name} was confirmed and the bin is cleaned. "
                               f"+{pts} points")
                        summary["points"] += pts
                    else:
                        msg = (f"Your report on {name} was resolved and the bin is cleaned. "
                               f"You reached today's points limit.")
                else:
                    msg = (f"The waste team reviewed your report on {name} and cleaned the bin. "
                           f"No points were awarded for this report.")
                add_in(conn, r["user_id"], msg, bid)
                summary["notified"] += 1

            others = (voters | followers) - reporters - {admin_id}
            for uid in others:
                add_in(conn, uid, f"{name} has been cleaned and is empty now.", bid)
                summary["notified"] += 1
            summary["bins"] += 1
            summary["reports"] += len(reps)
    return summary


def avg_response_hours():
    with get_conn() as conn:
        v = conn.execute(
            """SELECT AVG((julianday(r.resolved_at) - julianday(r.created_at)) * 24)
               FROM reports r
               WHERE r.status = 'resolved' AND r.resolved_at IS NOT NULL
                 AND EXISTS (SELECT 1 FROM clean_log c WHERE c.bin_id = r.bin_id
                   AND ABS(strftime('%s', c.cleaned_at) - strftime('%s', r.resolved_at)) <= 2)"""
        ).fetchone()[0]
    return v


def clean_history(limit=200):
    with get_conn() as conn:
        df = pd.read_sql_query(
            """SELECT c.cleaned_at, b.name AS bin, b.type, c.fill_before, u.name AS cleaned_by
               FROM clean_log c JOIN bins b ON b.bin_id = c.bin_id
               JOIN users u ON u.id = c.admin_id
               ORDER BY c.id DESC LIMIT ?""", conn, params=(limit,))
    if not df.empty:
        df["cleaned_at"] = df["cleaned_at"].apply(local_str)
        df["fill_before"] = df["fill_before"].round(0)
    return df