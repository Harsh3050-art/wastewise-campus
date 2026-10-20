import hashlib
import io
import re
import sqlite3
import uuid
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image

from services.db import get_conn
from services.notifications import add_in
from services.points import award_in

ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = ROOT / "data" / "uploads" / "submissions"

MAX_PER_DAY = 2            # per rolling 24 hours
MAX_PER_WEEK = 5           # per rolling 7 days
DUP_DISTANCE = 8           # photos this close (out of 64) count as the same photo
SIMILAR_DISTANCE = 14      # admins see a warning up to this distance
SAME_PAIR_DISTANCE = 6     # the two photos of one creation must differ more than this
FLAGS_FOR_REVIEW = 3
POINTS_APPROVED = 30
POINTS_CREATIVE = 40
PENALTY_FAKE = 20
MAX_PHOTO_BYTES = 5_000_000


# ------------------------------------------------------------ daily code word
def _salt():
    try:
        import streamlit as st
        value = st.secrets.get("CODE_SALT")
    except Exception:
        value = None
    return str(value) if value else "wastewise-default-salt"


def daily_code(day=None):
    """A 4-digit code that changes every day. Students show it in the finished photo."""
    day = day or date.today()
    digest = hashlib.sha256(f"{_salt()}:{day.isoformat()}".encode()).hexdigest()
    return f"{int(digest[:8], 16) % 10000:04d}"


# ------------------------------------------------------------------ photo tools
def load_image(data):
    if not data:
        raise ValueError("Please take both photos first.")
    if len(data) > MAX_PHOTO_BYTES:
        raise ValueError("A photo is too large (max 5 MB).")
    try:
        Image.open(io.BytesIO(data)).verify()
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        raise ValueError("One of the files is not a valid image.")
    img.thumbnail((1280, 1280))
    return img


def dhash(img, size=8):
    """64-bit 'difference hash': similar-looking photos get similar hashes."""
    g = img.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
    a = np.asarray(g, dtype=int)
    bits = (a[:, :-1] > a[:, 1:]).flatten()
    value = 0
    for b in bits:
        value = (value << 1) | int(b)
    return f"{value:016x}"


def hamming(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def save_jpeg(img):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.jpg"
    img.save(UPLOAD_DIR / name, "JPEG", quality=85)
    return f"data/uploads/submissions/{name}"


def norm_title(text):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", (text or "").lower())).strip()


def notify_admins(conn, message):
    for r in conn.execute("SELECT id FROM users WHERE role = 'admin'").fetchall():
        add_in(conn, r["id"], message)


# ------------------------------------------------------------- student side
def create_submission(user_id, title, materials, description, process_bytes, final_bytes):
    title, materials = (title or "").strip(), (materials or "").strip()
    description = (description or "").strip()
    if not 3 <= len(title) <= 80:
        return False, "Write what you made (3 to 80 characters)."
    if not 3 <= len(materials) <= 120:
        return False, "Write which waste items you used (3 to 120 characters)."
    if len(description) > 300:
        return False, "The description is too long (max 300 characters)."
    try:
        p_img, f_img = load_image(process_bytes), load_image(final_bytes)
    except ValueError as e:
        return False, str(e)
    p_hash, f_hash = dhash(p_img), dhash(f_img)
    if hamming(p_hash, f_hash) <= SAME_PAIR_DISTANCE:
        return False, "Your two photos look the same. Photo 1 shows the waste or work in progress, photo 2 the finished product."

    with get_conn() as conn:
        day = conn.execute("SELECT COUNT(*) FROM submissions WHERE user_id = ? "
                           "AND created_at >= datetime('now', '-1 day')", (user_id,)).fetchone()[0]
        if day >= MAX_PER_DAY:
            return False, f"You can share up to {MAX_PER_DAY} creations in 24 hours."
        week = conn.execute("SELECT COUNT(*) FROM submissions WHERE user_id = ? "
                            "AND created_at >= datetime('now', '-7 days')", (user_id,)).fetchone()[0]
        if week >= MAX_PER_WEEK:
            return False, f"You can share up to {MAX_PER_WEEK} creations per week."
        key = norm_title(title)
        for r in conn.execute("SELECT idea_title FROM submissions WHERE user_id = ? "
                              "AND status IN ('pending', 'approved') "
                              "AND created_at >= datetime('now', '-7 days')", (user_id,)):
            if norm_title(r["idea_title"]) == key:
                return False, "You already shared this idea in the last 7 days."
        for r in conn.execute("SELECT image_hash, process_hash FROM submissions"):
            for h in (r["image_hash"], r["process_hash"]):
                if h and (hamming(h, f_hash) <= DUP_DISTANCE or hamming(h, p_hash) <= DUP_DISTANCE):
                    return False, "One of these photos looks like a photo that was already shared. Please take new photos."
        p_path, f_path = save_jpeg(p_img), save_jpeg(f_img)
        conn.execute(
            "INSERT INTO submissions (user_id, idea_title, materials, description, "
            "process_photo_path, photo_path, image_hash, process_hash, daily_code) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (user_id, title, materials, description, p_path, f_path, f_hash, p_hash, daily_code()))
        name = conn.execute("SELECT name FROM users WHERE id = ?", (user_id,)).fetchone()[0]
        notify_admins(conn, f"New creation to review: '{title}' by {name}.")
    return True, "Submitted! An admin will review it, and you will get a notification with the result."


def my_submissions(user_id):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM submissions WHERE user_id = ? ORDER BY id DESC",
                            (user_id,)).fetchall()
    return [dict(r) for r in rows]


def gallery(viewer_id, limit=30):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT s.id, s.idea_title, s.materials, s.description, s.photo_path, s.user_id,
                      u.name AS user_name,
                      EXISTS(SELECT 1 FROM submission_flags f
                             WHERE f.submission_id = s.id AND f.user_id = ?) AS flagged_by_me
               FROM submissions s JOIN users u ON u.id = s.user_id
               WHERE s.status = 'approved' AND s.flag_review != 1
               ORDER BY s.reviewed_at DESC, s.id DESC LIMIT ?""", (viewer_id, limit)).fetchall()
    return [dict(r) for r in rows]


def flag_submission(user_id, submission_id, reason):
    reason = (reason or "").strip()[:200]
    with get_conn() as conn:
        s = conn.execute("SELECT user_id, status, flag_review, idea_title FROM submissions "
                         "WHERE id = ?", (submission_id,)).fetchone()
        if not s or s["status"] != "approved":
            return False, "Only approved creations can be flagged."
        if s["user_id"] == user_id:
            return False, "You cannot flag your own creation."
        try:
            conn.execute("INSERT INTO submission_flags (submission_id, user_id, reason) "
                         "VALUES (?,?,?)", (submission_id, user_id, reason))
        except sqlite3.IntegrityError:
            return False, "You already flagged this creation."
        n = conn.execute("SELECT COUNT(*) FROM submission_flags WHERE submission_id = ?",
                         (submission_id,)).fetchone()[0]
        if n >= FLAGS_FOR_REVIEW and s["flag_review"] == 0:
            conn.execute("UPDATE submissions SET flag_review = 1 WHERE id = ?", (submission_id,))
            notify_admins(conn, f"'{s['idea_title']}' was flagged by {n} students and needs another look.")
    return True, "Thanks, your flag was sent to the admins."


# --------------------------------------------------------------- admin side
def pending_list():
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT s.*, u.name AS user_name, u.hostel_or_dept,
                 (SELECT COUNT(*) FROM submissions x WHERE x.user_id = s.user_id
                    AND x.status = 'approved') AS user_approved,
                 (SELECT COUNT(*) FROM submissions x WHERE x.user_id = s.user_id
                    AND x.status = 'rejected') AS user_rejected,
                 (SELECT COUNT(*) FROM submissions x WHERE x.user_id = s.user_id
                    AND x.created_at >= datetime('now', '-7 days')) AS user_week
               FROM submissions s JOIN users u ON u.id = s.user_id
               WHERE s.status = 'pending' ORDER BY s.id""").fetchall()
    return [dict(r) for r in rows]


def flagged_list():
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT s.*, u.name AS user_name,
                 (SELECT COUNT(*) FROM submission_flags f WHERE f.submission_id = s.id) AS flag_count,
                 (SELECT GROUP_CONCAT(f.reason, ' | ') FROM submission_flags f
                    WHERE f.submission_id = s.id AND f.reason != '') AS flag_reasons
               FROM submissions s JOIN users u ON u.id = s.user_id
               WHERE s.status = 'approved' AND s.flag_review = 1 ORDER BY s.id""").fetchall()
    return [dict(r) for r in rows]


def counts():
    with get_conn() as conn:
        pending = conn.execute("SELECT COUNT(*) FROM submissions WHERE status = 'pending'").fetchone()[0]
        flagged = conn.execute("SELECT COUNT(*) FROM submissions WHERE status = 'approved' "
                               "AND flag_review = 1").fetchone()[0]
    return pending, flagged


def similar_to(submission_id, max_distance=SIMILAR_DISTANCE):
    """Other submissions with a photo that looks like one of this submission's photos."""
    with get_conn() as conn:
        me = conn.execute("SELECT image_hash, process_hash FROM submissions WHERE id = ?",
                          (submission_id,)).fetchone()
        others = conn.execute("SELECT id, idea_title, image_hash, process_hash FROM submissions "
                              "WHERE id != ?", (submission_id,)).fetchall()
    if not me:
        return []
    mine = [h for h in (me["image_hash"], me["process_hash"]) if h]
    out = []
    for o in others:
        theirs = [h for h in (o["image_hash"], o["process_hash"]) if h]
        if not mine or not theirs:
            continue
        d = min(hamming(a, b) for a in mine for b in theirs)
        if d <= max_distance:
            out.append({"id": o["id"], "title": o["idea_title"], "distance": d})
    return sorted(out, key=lambda x: x["distance"])[:3]


def approve(submission_id, admin_id, creative=False):
    pts = POINTS_CREATIVE if creative else POINTS_APPROVED
    with get_conn() as conn:
        s = conn.execute("SELECT user_id, idea_title, status FROM submissions WHERE id = ?",
                         (submission_id,)).fetchone()
        if not s or s["status"] != "pending":
            return False, "This creation is no longer pending."
        award_in(conn, s["user_id"], pts, "creation_approved", f"submission:{submission_id}")
        conn.execute("UPDATE submissions SET status = 'approved', reviewed_by = ?, "
                     "reviewed_at = CURRENT_TIMESTAMP, points_awarded = ?, review_note = ? "
                     "WHERE id = ?", (admin_id, pts, "Creative bonus" if creative else "", submission_id))
        add_in(conn, s["user_id"], f"Your creation '{s['idea_title']}' was approved. +{pts} points")
    return True, f"Approved. {pts} points given."


def reject(submission_id, admin_id, reason, fake=False):
    reason = (reason or "").strip()
    if len(reason) < 3:
        return False, "Please write a reason for the rejection."
    with get_conn() as conn:
        s = conn.execute("SELECT user_id, idea_title, status FROM submissions WHERE id = ?",
                         (submission_id,)).fetchone()
        if not s or s["status"] != "pending":
            return False, "This creation is no longer pending."
        if fake:
            award_in(conn, s["user_id"], -PENALTY_FAKE, "creation_fake", f"submission:{submission_id}")
        conn.execute("UPDATE submissions SET status = 'rejected', reviewed_by = ?, "
                     "reviewed_at = CURRENT_TIMESTAMP, points_awarded = ?, review_note = ? "
                     "WHERE id = ?", (admin_id, -PENALTY_FAKE if fake else 0, reason, submission_id))
        msg = f"Your creation '{s['idea_title']}' was not approved. Reason: {reason.rstrip('.')}."
        if fake:
            msg += f" A penalty of {PENALTY_FAKE} points was applied."
        add_in(conn, s["user_id"], msg)
    return True, "Rejected." if not fake else f"Rejected as fake. {PENALTY_FAKE} points taken."


def resolve_flag(submission_id, admin_id, revoke, note=""):
    note = (note or "").strip()
    with get_conn() as conn:
        s = conn.execute("SELECT user_id, idea_title, status, flag_review, points_awarded "
                         "FROM submissions WHERE id = ?", (submission_id,)).fetchone()
        if not s or s["status"] != "approved" or s["flag_review"] != 1:
            return False, "This creation is not waiting for a flag review."
        if not revoke:
            conn.execute("UPDATE submissions SET flag_review = 2 WHERE id = ?", (submission_id,))
            return True, "Kept as approved."
        if len(note) < 3:
            return False, "Please write a reason for withdrawing the approval."
        if s["points_awarded"] > 0:
            award_in(conn, s["user_id"], -s["points_awarded"], "creation_revoked",
                     f"submission:{submission_id}")
        conn.execute("UPDATE submissions SET status = 'rejected', flag_review = 2, "
                     "points_awarded = 0, review_note = ?, reviewed_by = ?, "
                     "reviewed_at = CURRENT_TIMESTAMP WHERE id = ?", (note, admin_id, submission_id))
        add_in(conn, s["user_id"],
               f"Your creation '{s['idea_title']}' was reviewed again and the approval was withdrawn. Reason: {note.rstrip('.')}.")
    return True, "Approval withdrawn and points taken back."