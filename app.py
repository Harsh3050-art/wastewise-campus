
import hmac
import streamlit as st

from services.db import init_db
from services.auth import (
    signup, login, current_user, sidebar_user
)

st.set_page_config(
    page_title="WasteWise Campus",
    page_icon="♻️",
    layout="wide"
)

init_db()


def get_admin_code():
    try:
        return st.secrets["ADMIN_INVITE_CODE"]
    except Exception:
        return None


user = current_user()

if user:
    sidebar_user()
    st.title(f"Welcome, {user['name']}")
    st.caption(f"Role: {user['role']}")
    st.write("Use the sidebar to open the pages.")
    st.stop()


st.title("WasteWise Campus")
st.caption("Smart and sustainable waste management for IIT Roorkee")

tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

with tab_login:
    with st.form("login_form"):
        ident = st.text_input("Email or enrollment ID")
        pw = st.text_input("Password", type="password")
        go = st.form_submit_button("Log in")

    if go:
        u = login(ident, pw)

        if u:
            st.session_state["user"] = u
            st.rerun()
        else:
            st.error("Wrong ID or password.")


with tab_signup:
    with st.form("signup_form"):
        name = st.text_input("Full name")
        ident2 = st.text_input(
            "Email or enrollment ID",
            key="signup_ident"
        )
        hostel = st.text_input(
            "Hostel or department (optional)"
        )
        pw1 = st.text_input(
            "Password (min 8 characters)",
            type="password",
            key="pw1"
        )
        pw2 = st.text_input(
            "Confirm password",
            type="password",
            key="pw2"
        )
        code = st.text_input(
            "Admin invite code (waste team only, otherwise leave blank)",
            type="password"
        )
        go2 = st.form_submit_button("Create account")

    if go2:
        role = "student"

        if code.strip():
            expected = get_admin_code()

            if expected and hmac.compare_digest(
                code.strip(), expected
            ):
                role = "admin"
            else:
                st.error("Invalid admin invite code.")
                st.stop()

        ok, msg = signup(
            name, ident2, pw1, pw2, hostel, role
        )
        (st.success if ok else st.error)(msg)
