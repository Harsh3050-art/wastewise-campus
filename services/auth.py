
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

def hide_sidebar():
    """Hide the whole sidebar (used on the login screen)."""
    st.markdown(
        """<style>
        [data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="collapsedControl"] { display: none; }
        </style>""",
        unsafe_allow_html=True)
def require_login():
    if not current_user():
        hide_sidebar()
        st.warning("Please log in first.")
        st.page_link("Home.py", label="Go to the login page", icon="🔑")
        st.stop()


def require_admin():
    require_login()
    if current_user()["role"] != "admin":
        st.error("This page is only for the waste management team.")
        st.stop()

ADMIN_HIDDEN_PAGES = ["Reuse_Coach", "Profile", "Share_Creation"]
STUDENT_HIDDEN_PAGES = ["Admin_Dashboard"]


def hide_nav_links(page_names):
    """Hide entries from the sidebar page list (the pages themselves are also guarded)."""
    rules = ", ".join(
        f'[data-testid="stSidebarNav"] a[href$="/{n}"], [data-testid="stSidebarNavLink"][href$="/{n}"]'
        for n in page_names)
    st.markdown(f"<style>{rules} {{ display: none; }}</style>", unsafe_allow_html=True)

def sidebar_user(poll=False):
    u = current_user()
    if u:
        toast_new(u["id"])
        hide_nav_links(["Notifications"] + (ADMIN_HIDDEN_PAGES if u["role"] == "admin" else STUDENT_HIDDEN_PAGES))
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

def change_password(user_id, old, new, confirm):
    if len(new) < MIN_PASSWORD:
        return False, f"Password must be at least {MIN_PASSWORD} characters."
    if len(new.encode("utf-8")) > 72:
        return False, "Password is too long (max 72 bytes)."
    if new != confirm:
        return False, "The new passwords do not match."

    with get_conn() as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()

        if not row or not verify_password(old, row["password_hash"]):
            return False, "Your current password is wrong."

        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new), user_id)
        )

    return True, "Password changed."
