
import streamlit as st
from services.db import get_conn


def add_in(conn, user_id, message, bin_id=None):
    conn.execute(
        "INSERT INTO notifications (user_id, bin_id, message) VALUES (?,?,?)",
        (user_id, bin_id, message)
    )


def unread_count(user_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM notifications "
            "WHERE user_id = ? AND is_read = 0",
            (user_id,)
        ).fetchone()[0]


def list_for(user_id, limit=50):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM notifications "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


def mark_all_read(user_id):
    with get_conn() as conn:
        conn.execute(
            "UPDATE notifications SET is_read = 1 WHERE user_id = ?",
            (user_id,)
        )


def toast_new(user_id):
    """Show new unread notifications."""
    last = st.session_state.get("last_toast_id")

    with get_conn() as conn:
        max_id = conn.execute(
            "SELECT COALESCE(MAX(id), 0) "
            "FROM notifications WHERE user_id = ?",
            (user_id,)
        ).fetchone()[0]

        if last is None:
            rows = conn.execute(
                "SELECT message FROM notifications "
                "WHERE user_id = ? AND is_read = 0 "
                "ORDER BY id DESC LIMIT 3",
                (user_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT message FROM notifications "
                "WHERE user_id = ? AND is_read = 0 "
                "AND id > ? ORDER BY id",
                (user_id, last)
            ).fetchall()

    st.session_state["last_toast_id"] = max_id

    for r in rows:
        st.toast(r["message"], icon="🔔")
