import pandas as pd
import streamlit as st

from services import profile as pf
from services import submissions as sb
from services.auth import require_login, sidebar_user, current_user, change_password
from services.stats import user_stats, badge_info
from services.timeutil import ago, local_str

st.set_page_config(page_title="My profile", layout="wide")
require_login()
sidebar_user()
user = current_user()
if user["role"] == "admin":
    st.info("This page is for students.")
    st.stop()
    
me = pf.get_profile(user["id"])

st.title("My profile")
st.subheader(me["name"])
st.caption(f"{me['identifier']} | {me['role']} | "
           f"{me['hostel_or_dept'] or 'no hostel or department set'} | joined {local_str(me['created_at'])}")


def settings_block():
    with st.form("group_form"):
        grp = st.text_input("Hostel or department", value=me["hostel_or_dept"] or "", max_chars=60)
        saved = st.form_submit_button("Save")
    if saved:
        pf.update_group(user["id"], grp)
        st.success("Saved. It will show on the leaderboard from now on.")
    with st.form("pw_form"):
        old = st.text_input("Current password", type="password")
        new = st.text_input("New password (min 8 characters)", type="password")
        conf = st.text_input("Confirm new password", type="password")
        changed = st.form_submit_button("Change password")
    if changed:
        ok, msg = change_password(user["id"], old, new, conf)
        (st.success if ok else st.error)(msg)


if me["role"] != "student":
    st.subheader("Settings")
    settings_block()
    st.stop()

s = user_stats(user["id"])
badge, nxt, to_go, ratio = badge_info(s["points"])
c1, c2, c3, c4 = st.columns(4)
with c1.container(border=True):
    st.metric("Points", s["points"])
with c2.container(border=True):
    st.metric("Rank", f"#{s['rank']}")
with c3.container(border=True):
    st.metric("Badge", badge)
with c4.container(border=True):
    st.metric("Creations approved", s["makes"])
if nxt:
    st.progress(ratio, text=f"{to_go} points to reach {nxt}")
else:
    st.success("You reached the top badge!")

tab1, tab2, tab3, tab4 = st.tabs(["My reports", "My creations", "Points history", "Settings"])

with tab1:
    rows = pf.my_reports(user["id"])
    if not rows:
        st.info("You have not reported any bin yet.")
    else:
        df = pd.DataFrame(rows)
        df["when"] = df["created_at"].apply(ago)
        st.dataframe(df[["bin_name", "tag", "status", "when"]].rename(columns={
            "bin_name": "Bin", "tag": "Problem", "status": "Status", "when": "Reported"}),
            hide_index=True)

with tab2:
    subs = sb.my_submissions(user["id"])
    if not subs:
        st.info("You have not shared a creation yet.")
    else:
        df = pd.DataFrame(subs)
        df["when"] = df["created_at"].apply(ago)
        st.dataframe(df[["idea_title", "status", "points_awarded", "review_note", "when"]].rename(
            columns={"idea_title": "Creation", "status": "Status", "points_awarded": "Points",
                     "review_note": "Admin note", "when": "Shared"}), hide_index=True)

with tab3:
    rows = pf.points_history(user["id"])
    if not rows:
        st.info("No points yet. Report a bin, try an idea, or share a creation.")
    else:
        df = pd.DataFrame(rows)
        df["when"] = df["created_at"].apply(ago)
        st.dataframe(df[["when", "points", "reason"]].rename(columns={
            "when": "When", "points": "Points", "reason": "Why"}), hide_index=True)

with tab4:
    settings_block()