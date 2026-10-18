import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

from services import reports as rp
from services.auth import require_login, sidebar_user, current_user
from services.bins import get_all_bins, get_readings
from services.follows import is_following, follow, unfollow
from services.mapview import build_map, nearest_bin, TYPE_LABEL
from services.timeutil import ago

st.set_page_config(page_title="Campus Map", layout="wide")
require_login()
sidebar_user()
user = current_user()

df_all = get_all_bins()
if df_all.empty:
    st.warning("No bins found. Run setup_db.py first.")
    st.stop()

STATUS_LABEL = {"green": "Green (under 50%)", "yellow": "Yellow (50-80%)", "red": "Red (80%+)"}
SIZES = ["small", "medium", "large", "bulk"]
default_view = {"center": [float(df_all["lat"].mean()), float(df_all["lng"].mean())], "zoom": 17}

with st.sidebar:
    st.divider()
    st.subheader("Map filters")
    types = st.multiselect("Bin type", list(TYPE_LABEL), default=list(TYPE_LABEL),
                           format_func=TYPE_LABEL.get)
    sizes = st.multiselect("Bin size", SIZES, default=SIZES)
    statuses = st.multiselect("Fill status", list(STATUS_LABEL), default=list(STATUS_LABEL),
                              format_func=STATUS_LABEL.get)
    live = st.toggle("Live updates (every 10 s)")
    if st.button("Reset map view"):
        st.session_state["map_view"] = default_view
        st.session_state["selected_bin"] = ""

if live:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=10_000, key="map_refresh")

df = df_all[df_all["type"].isin(types) & df_all["size"].isin(sizes)
            & df_all["status"].isin(statuses)]

# coming from the student home ("Show on map")
focus = st.session_state.pop("focus_bin", None)
if focus and focus in set(df_all["bin_id"]):
    row = df_all[df_all["bin_id"] == focus].iloc[0]
    st.session_state["selected_bin"] = focus
    st.session_state["map_view"] = {"center": [float(row["lat"]), float(row["lng"])], "zoom": 19}
view = st.session_state.setdefault("map_view", default_view)

st.title("Campus Map")
st.caption(f"Showing {len(df)} of {len(df_all)} bins. Colour = fill level, "
           f"ring and letter = bin type, size = capacity, red badge = open reports.")

col_map, col_info = st.columns([2.2, 1], gap="medium")

with col_map:
    m = build_map(df, view["center"], view["zoom"], st.session_state.get("selected_bin") or None)
    out = st_folium(m, key="campus_map", height=620, use_container_width=True,
                    returned_objects=["last_object_clicked", "center", "zoom"])
    if out:
        c, z = out.get("center"), out.get("zoom")
        if c and z:
            st.session_state["map_view"] = {"center": [c["lat"], c["lng"]], "zoom": z}
        clk = out.get("last_object_clicked")
        if clk and clk != st.session_state.get("last_click"):
            st.session_state["last_click"] = clk
            hit = nearest_bin(df, clk["lat"], clk["lng"])
            if hit:
                st.session_state["selected_bin"] = hit

with col_info:
    flash = st.session_state.pop("map_flash", None)
    if flash:
        st.success(flash)

    names = dict(zip(df_all["bin_id"], df_all["name"]))
    st.selectbox(
        "Selected bin", [""] + df_all["bin_id"].tolist(), key="selected_bin",
        format_func=lambda i: "Click a bin on the map or pick one here" if i == "" else f"{names[i]} ({i})")
    sel = st.session_state.get("selected_bin")
    if sel:
        r = df_all[df_all["bin_id"] == sel].iloc[0]
        with st.container(border=True):
            st.subheader(r["name"])
            st.caption(f"{TYPE_LABEL[r['type']]} bin | {r['size']} | {int(r['capacity_litres'])} L")
            st.progress(min(max(r["fill_pct"], 0), 100) / 100, text=f"{r['fill_pct']:.0f}% full")
            st.write(f"**Status:** {r['status']}")
            st.write(f"**Prediction:** {r['eta_text']}")
            last = r["last_cleaned_at"]
            st.write(f"**Last cleaned:** {last if pd.notna(last) else 'no record yet'}")
            st.write(f"**Open reports:** {int(r['open_reports'])}")
        rd = get_readings(sel)
        if len(rd) > 1:
            fig = px.line(rd, x="recorded_at", y="fill_pct", title="Recent fill level (%)")
            fig.update_layout(height=240, margin=dict(l=10, r=10, t=40, b=10),
                              yaxis_range=[0, 100], xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig)
        else:
            st.caption("No readings yet. Run the simulator to see the trend.")

        st.divider()
        if user["role"] == "student":
            following = is_following(user["id"], sel)
            label = "Unfollow this bin" if following else "Follow this bin (get notified when cleaned)"
            if st.button(label, key=f"follow_{sel}"):
                (unfollow if following else follow)(user["id"], sel)
                st.rerun()
            with st.expander("Report this bin"):
                with st.form(f"report_form_{sel}", clear_on_submit=True):
                    tag = st.selectbox("What is the problem?", rp.TAGS)
                    comment = st.text_area("Comment (optional)", max_chars=rp.MAX_COMMENT,
                                           placeholder="For example: overflowing since morning, please clean.")
                    photo = st.file_uploader("Photo (optional)", type=["jpg", "jpeg", "png"])
                    go = st.form_submit_button("Submit report", type="primary")
                if go:
                    ok, msg = rp.create_report(user["id"], sel, tag, comment, photo)
                    if ok:
                        st.session_state["map_flash"] = msg
                        st.rerun()
                    else:
                        st.error(msg)
        else:
            st.info("Admins clean bins from the Admin Dashboard.")
            st.page_link("pages/6_Admin_Dashboard.py", label="Open the admin dashboard", icon="🛠️")

        threads = rp.get_reports(sel, user["id"])
        open_r = [x for x in threads if x["status"] == "open"]
        done_r = [x for x in threads if x["status"] == "resolved"]
        st.subheader(f"Reports ({len(open_r)} open)")
        if not open_r:
            st.caption("No open reports for this bin.")
        for x in open_r:
            with st.container(border=True):
                st.write(f"**{x['tag']}** by {x['user_name']} ({ago(x['created_at'])})")
                if x["comment"]:
                    st.write(x["comment"])
                if x["photo_path"]:
                    st.image(rp.photo_abs(x["photo_path"]), width=200)
                st.caption(f"{x['upvotes']} people said me too")
                if user["role"] == "student" and x["user_id"] != user["id"] and not x["voted"]:
                    if st.button("Me too", key=f"vote_{x['id']}"):
                        ok, msg = rp.upvote(x["id"], user["id"])
                        st.session_state["map_flash"] = msg
                        st.rerun()
        if done_r:
            with st.expander(f"Resolved reports ({len(done_r)})"):
                for x in done_r[:10]:
                    st.write(f"{x['tag']} by {x['user_name']} ({ago(x['created_at'])})")
    else:
        st.info("Select a bin to see its details.")