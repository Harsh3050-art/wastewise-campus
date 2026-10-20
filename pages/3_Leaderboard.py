import streamlit as st

from services import leaderboard as lb
from services import submissions as sb
from services.auth import require_login, sidebar_user, current_user
from services.reports import photo_abs
from services.stats import badge_info

st.set_page_config(page_title="Leaderboard", layout="wide")
require_login()
sidebar_user()
user = current_user()

st.title("Leaderboard")
st.caption("Only verified points count: bin reports confirmed by the waste team and "
           "creations approved by an admin.")


def show_board(df):
    if df.empty:
        st.info("No students yet.")
        return
    top = df[df["points"] > 0].head(3)
    if not top.empty:
        cols = st.columns(len(top))
        for col, (_, r) in zip(cols, top.iterrows()):
            with col.container(border=True):
                st.metric(f"#{int(r['rank'])} {r['name']}", f"{int(r['points'])} points")
                extra = f" | {r['group_name']}" if r["group_name"] else ""
                st.caption(badge_info(int(r["points"]))[0] + extra)
    view = df.head(20).copy()
    view["name"] = view.apply(lambda r: r["name"] + (" (you)" if r["id"] == user["id"] else ""), axis=1)
    view["badge"] = view["points"].apply(lambda p: badge_info(int(p))[0])
    st.dataframe(
        view[["rank", "name", "group_name", "badge", "points"]].rename(columns={
            "rank": "Rank", "name": "Name", "group_name": "Hostel / dept",
            "badge": "Badge", "points": "Points"}),
        hide_index=True)
    me = df[df["id"] == user["id"]]
    if not me.empty and me.index[0] >= 20:
        st.caption(f"Your rank: #{int(me.iloc[0]['rank'])} with {int(me.iloc[0]['points'])} points.")


tab1, tab2, tab3, tab4 = st.tabs(["All-time", "This week", "Hostels and departments", "Gallery"])

with tab1:
    show_board(lb.all_time())
with tab2:
    show_board(lb.weekly())
with tab3:
    groups = lb.by_group()
    if groups.empty:
        st.info("Add your hostel or department in your profile to appear here.")
    else:
        st.dataframe(groups.rename(columns={
            "group_name": "Hostel / dept", "members": "Students",
            "total": "Total points", "average": "Average per student"}), hide_index=True)

with tab4:
    st.caption("Approved creations from your campus. If something does not look genuine, flag it.")
    items = sb.gallery(user["id"])
    if not items:
        st.info("No approved creations yet.")
    for i in range(0, len(items), 3):
        cols = st.columns(3)
        for col, it in zip(cols, items[i:i + 3]):
            with col.container(border=True):
                st.image(photo_abs(it["photo_path"]))
                st.markdown(f"**{it['idea_title']}**")
                st.caption(f"By {it['user_name']} | Made from: {it['materials']}")
                if it["description"]:
                    st.write(it["description"])
                if user["role"] == "student" and it["user_id"] != user["id"] and not it["flagged_by_me"]:
                    with st.expander("Report a problem"):
                        reason = st.text_input("What looks wrong?", key=f"fr_{it['id']}", max_chars=200)
                        if st.button("Send flag", key=f"fb_{it['id']}"):
                            ok, msg = sb.flag_submission(user["id"], it["id"], reason)
                            (st.success if ok else st.error)(msg)