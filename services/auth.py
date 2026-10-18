
import bcrypt
import streamlit as st
from services.db import get_conn
from services.alerts import render_alerts
from services.notifications import unread_count, toast_new

MIN_PASSWORD = 8


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            hashed.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def signup(
    name, identifier, password, confirm,
    hostel_or_dept="", role="student"
):
    name = name.strip()
    identifier = identifier.strip().lower()

    if not name:
        return False, "Please enter your name."
    if len(identifier) < 3:
        return False, "Enter a valid email or enrollment ID."
    if len(password) < MIN_PASSWORD:
        return False, "Password must be at least 8 characters."
    if len(password.encode("utf-8")) > 72:
        return False, "Password is too long (max 72 bytes)."
    if password != confirm:
        return False, "Passwords do not match."
    if role not in ("student", "admin"):
        return False, "Invalid account role."

    with get_conn() as conn:
        exists = conn.execute(
            "SELECT 1 FROM users WHERE identifier = ?",
            (identifier,)
        ).fetchone()

        if exists:
            return False, "This email or ID is already registered."

        conn.execute(
            """
            INSERT INTO users (
                name, identifier, password_hash,
                role, hostel_or_dept
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name, identifier, hash_password(password),
                role, hostel_or_dept.strip()
            ),
        )

    return True, "Account created. You can log in now."


def login(identifier, password):
    identifier = identifier.strip().lower()

    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE identifier = ?",
            (identifier,)
        ).fetchone()

    if row and verify_password(password, row["password_hash"]):
        return {
            "id": row["id"],
            "name": row["name"],
            "identifier": row["identifier"],
            "role": row["role"],
        }

    return None


def current_user():
    return st.session_state.get("user")


def logout():
    st.session_state.pop("user", None)


def require_login():
    if not current_user():
        st.warning("Please log in from the Home page first.")
        st.stop()


def require_admin():
    require_login()
    if current_user()["role"] != "admin":
        st.error("This page is only for the waste management team.")
        st.stop()


def sidebar_user(poll=False):
    u = current_user()
    if u:
        toast_new(u["id"])
        with st.sidebar:
            st.write(f"Logged in as **{u['name']}** ({u['role']})")
            n = unread_count(u["id"])
            st.page_link("pages/5_Notifications.py",
                         label=f"Notifications ({n})" if n else "Notifications", icon="🔔")
            if st.button("Log out", key="logout_btn"):
                logout()
                st.rerun()
            if u["role"] == "admin":
                st.divider()
                st.subheader("Fill alerts")
                render_alerts(5, compact=True)
        if poll:
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=15_000, key="notif_poll")