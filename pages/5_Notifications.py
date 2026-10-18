import streamlit as st
from services.auth import require_login, sidebar_user, current_user
from services.notifications import list_for, mark_all_read
from services.timeutil import ago, local_str

st.set_page_config(page_title="Notifications", layout="wide")
require_login()
sidebar_user(poll=True)
user = current_user()

st.title("Notifications")
items = list_for(user["id"])
if not items:
    st.info("No notifications yet. You will see updates here when a bin you reported or follow is cleaned.")
else:
    if any(not i["is_read"] for i in items):
        if st.button("Mark all as read"):
            mark_all_read(user["id"])
            st.rerun()
    for i in items:
        with st.container(border=True):
            prefix = "🆕 " if not i["is_read"] else ""
            st.write(f"{prefix}{i['message']}")
            st.caption(f"{ago(i['created_at'])} | {local_str(i['created_at'])}")