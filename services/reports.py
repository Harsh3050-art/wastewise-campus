import sqlite3
import uuid
from pathlib import Path

from PIL import Image

from services.db import get_conn
from services.notifications import add_in

ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = ROOT / "data" / "uploads" / "reports"

TAGS = ["Almost full", "Overflowing", "Bad smell", "Damaged", "Wrong waste inside", "Missing lid"]
MAX_COMMENT = 300
MAX_PER_DAY = 5
MAX_PHOTO_BYTES = 3_000_000


def photo_abs(rel_path):
    return str(ROOT / rel_path)


def save_photo(uploaded):
    if uploaded is None:
        return None
    if uploaded.size > MAX_PHOTO_BYTES:
        raise ValueError("Photo is too large (max 3 MB).")
    try:
        Image.open(uploaded).verify()
        uploaded.seek(0)
        img = Image.open(uploaded).convert("RGB")
    except Exception:
        raise ValueError("That file is not a valid image.")
    img.thumbnail((1280, 1280))
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.jpg"
    img.save(UPLOAD_DIR / name, "JPEG", quality=85)
    return f"data/uploads/reports/{name}"


def create_report(user_id, bin_id, tag, comment, photo=None):
    comment = (comment or "").strip()
    if tag not in TAGS:
        return False, "Please choose what the problem is."
    if len(comment) > MAX_COMMENT:
        return False, f"Comment is too long (max {MAX_COMMENT} characters)."
    with get_conn() as conn:
        if not conn.execute("SELECT 1 FROM bins WHERE bin_id = ? AND active = 1",
                            (bin_id,)).fetchone():
            return False, "This bin was not found."
        if conn.execute("SELECT 1 FROM reports WHERE bin_id = ? AND user_id = ? AND status = 'open'",
                        (bin_id, user_id)).fetchone():
            return False, "You already have an open report on this bin. Tap 'Me too' on other reports instead."
        today = conn.execute(
            "SELECT COUNT(*) FROM reports WHERE user_id = ? AND date(created_at) = date('now')",
            (user_id,)).fetchone()[0]
        if today >= MAX_PER_DAY:
            return False, f"You can send up to {MAX_PER_DAY} reports per day."
        try:
            photo_path = save_photo(photo)
        except ValueError as e:
            return False, str(e)
        conn.execute(
            "INSERT INTO reports (bin_id, user_id, tag, comment, photo_path) VALUES (?,?,?,?,?)",
            (bin_id, user_id, tag, comment, photo_path))
    return True, "Report sent. The waste team can see it now."


def get_reports(bin_id, viewer_id):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT r.*, u.name AS user_name,
                      EXISTS(SELECT 1 FROM report_votes v
                             WHERE v.report_id = r.id AND v.user_id = ?) AS voted
               FROM reports r JOIN users u ON u.id = r.user_id
               WHERE r.bin_id = ? ORDER BY r.id DESC""", (viewer_id, bin_id)).fetchall()
    return [dict(r) for r in rows]


def open_reports_all():
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT r.*, u.name AS user_name, b.name AS bin_name
               FROM reports r JOIN users u ON u.id = r.user_id
               JOIN bins b ON b.bin_id = r.bin_id
               WHERE r.status = 'open' ORDER BY r.upvotes DESC, r.id""").fetchall()
    return [dict(r) for r in rows]


def upvote(report_id, user_id):
    with get_conn() as conn:
        r = conn.execute("SELECT user_id, status FROM reports WHERE id = ?",
                         (report_id,)).fetchone()
        if not r or r["status"] != "open":
            return False, "This report is no longer open."
        if r["user_id"] == user_id:
            return False, "You cannot vote on your own report."
        try:
            conn.execute("INSERT INTO report_votes (report_id, user_id) VALUES (?,?)",
                         (report_id, user_id))
        except sqlite3.IntegrityError:
            return False, "You already said 'me too' on this report."
        conn.execute("UPDATE reports SET upvotes = upvotes + 1 WHERE id = ?", (report_id,))
    return True, "Thanks, your vote was added."


def dismiss_report(report_id, admin_id):
    with get_conn() as conn:
        r = conn.execute(
            "SELECT r.user_id, r.bin_id, b.name FROM reports r "
            "JOIN bins b ON b.bin_id = r.bin_id WHERE r.id = ? AND r.status = 'open'",
            (report_id,)).fetchone()
        if not r:
            return False
        conn.execute("UPDATE reports SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP "
                     "WHERE id = ?", (report_id,))
        add_in(conn, r["user_id"],
               f"The waste team reviewed your report on {r['name']} and closed it without cleaning.",
               r["bin_id"])
    return True
def all_reports(status=None, limit=200):
    """Reports from every bin, newest first. status: None (all), 'open' or 'resolved'."""
    sql = ("SELECT r.*, u.name AS user_name, b.name AS bin_name "
           "FROM reports r JOIN users u ON u.id = r.user_id "
           "JOIN bins b ON b.bin_id = r.bin_id")
    params = []
    if status in ("open", "resolved"):
        sql += " WHERE r.status = ?"
        params.append(status)
    sql += " ORDER BY r.id DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]