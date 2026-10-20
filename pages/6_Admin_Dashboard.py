import plotly.express as px
import streamlit as st
import pandas as pd
from services import submissions as sb
from ml.forecast import load_meta, hourly_profile, train
from ml.simulator import advance, backfill
from services import reports as rp
from services.alerts import render_alerts
from services.auth import require_admin, sidebar_user, current_user
from services.cleaning import mark_cleaned, avg_response_hours, clean_history
from services.stats import admin_kpis
from services.timeutil import ago
from services.summary import daily_brief
st.set_page_config(page_title="Admin Dashboard", layout="wide")
require_admin()
sidebar_user()
admin = current_user()

with st.sidebar:
    if st.toggle("Live updates (every 10 s)"):
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=10_000, key="admin_refresh")

df, k = admin_kpis()

st.title("Admin Dashboard")
flash = st.session_state.pop("admin_flash", None)
if flash:
    st.success(flash)
if k["pending_creations"] or k["flagged_creations"]:
    st.warning(
        f"{k['pending_creations']} creation(s) are waiting for your review and "
        f"{k['flagged_creations']} flagged by students. Open the last tab."
    )
r1 = st.columns(3)
with r1[0].container(border=True):
    st.metric("Total bins", k["total"])
with r1[1].container(border=True):
    st.metric("Above 80% full", k["above80"])
with r1[2].container(border=True):
    st.metric("Full within 6 hours", k["within6"])

r2 = st.columns(3)
with r2[0].container(border=True):
    st.metric("Average fill", f"{k['avg_fill']:.0f}%")
with r2[1].container(border=True):
    st.metric("Open reports", k["open_reports"])
with r2[2].container(border=True):
    st.metric("Cleaned today", k["cleaned_today"])

r3 = st.columns(3)

with r3[0].container(border=True):
    st.metric("Creations to review", k["pending_creations"])

with r3[1].container(border=True):
    st.metric("Flagged creations", k["flagged_creations"])

def demo_controls_enabled():
    try:
        return str(st.secrets.get("DEMO_MODE", "true")).lower() != "false"
    except Exception:
        return True


if demo_controls_enabled():
    with st.expander("Simulation controls (demo only)"):
        st.caption(
            "There are no real sensors, so these buttons move the simulated clock forward "
            "and refill the bins. Real sensors would write the same readings."
        )
        b1, b2, b3, b4 = st.columns(4)
        moved = None

        if b1.button("Advance 1 hour"):
            advance(1)
            moved = "Moved the simulation forward by 1 hour."

        if b2.button("Advance 6 hours"):
            advance(6)
            moved = "Moved the simulation forward by 6 hours."

        if b3.button("Advance 24 hours"):
            advance(24)
            moved = "Moved the simulation forward by 24 hours."

        if b4.button("Reset to realistic levels"):
            with st.spinner("Rebuilding 28 days of history..."):
                backfill(28)
            moved = "Bin levels were rebuilt from 28 days of simulated history."

        if moved:
            st.session_state["admin_flash"] = moved
            st.rerun()
with st.expander("Today's brief", expanded=True):
    for line in daily_brief():
        st.write("- " + line)
st.subheader("Top 5 bins about to fill")
render_alerts(5)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Priority list and cleaning",
        "Open reports",
        "Cleaning history",
        "Overview",
        "Forecast model",
        f"Creations to review ({k['pending_creations'] + k['flagged_creations']})",
    ]
)

with tab1:
    ranked = df.sort_values("priority", ascending=False).copy()
    ranked["why"] = ranked.apply(
        lambda r: f"{r['eta_text']}; {int(r['open_reports'])} open report(s)", axis=1)
    st.caption("Priority = 50% urgency (time to full) + 30% fill level + 20% open reports.")
    st.dataframe(ranked[["bin_id", "name", "type", "fill_pct", "priority", "why"]],
                 hide_index=True)

    st.subheader("Mark bins as cleaned")
    names = dict(zip(ranked["bin_id"], ranked["name"]))
    pick = st.multiselect("Bins you have cleaned", ranked["bin_id"].tolist(),
                          format_func=lambda i: f"{names[i]} ({i})")
    valid = st.checkbox("Open reports on these bins are valid (give points to reporters)",
                        value=True)
    if st.button("Mark selected as cleaned", type="primary", disabled=not pick):
        res = mark_cleaned(pick, admin["id"], valid)
        st.session_state["admin_flash"] = (
            f"Cleaned {res['bins']} bin(s), resolved {res['reports']} report(s), "
            f"sent {res['notified']} notification(s).")
        st.rerun()

with tab2:
    view = st.radio("Show", ["Open", "Resolved", "All"], horizontal=True, key="report_view")
    if view == "Open":
        items = rp.open_reports_all()
    else:
        items = rp.all_reports("resolved" if view == "Resolved" else None)
    if not items:
        st.info(f"No {view.lower()} reports.")
    for x in items:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.write(f"**{x['bin_name']}** ({x['bin_id']}): {x['tag']} | {x['status']}")
                if x["comment"]:
                    st.write(x["comment"])
                note = f"By {x['user_name']} | {ago(x['created_at'])} | {x['upvotes']} me too"
                if x["status"] == "resolved" and x["resolved_at"]:
                    note += f" | resolved {ago(x['resolved_at'])}"
                st.caption(note)
            with c2:
                if x["photo_path"]:
                    st.image(rp.photo_abs(x["photo_path"]), width=120)
            if x["status"] == "open" and st.button("Dismiss (not valid)", key=f"dismiss_{x['id']}"):
                rp.dismiss_report(x["id"], admin["id"])
                st.session_state["admin_flash"] = "Report dismissed."
                st.rerun()

with tab3:
    avg = avg_response_hours()
    hist = clean_history()
    m1, m2 = st.columns(2)
    m1.metric("Average response time", f"{avg:.1f} h" if avg is not None else "no data yet")
    m2.metric("Cleanings shown", len(hist))
    if hist.empty:
        st.info("No cleanings logged yet.")
    else:
        st.dataframe(hist, hide_index=True)

with tab4:
    c1, c2 = st.columns(2)
    with c1:
        status = df["status"].value_counts().reindex(
            ["green", "yellow", "red"], fill_value=0).reset_index()
        status.columns = ["status", "bins"]
        fig1 = px.bar(status, x="status", y="bins", color="status", title="Bins by fill status",
                      color_discrete_map={"green": "#2e9e5b", "yellow": "#f2b01e", "red": "#d64545"})
        fig1.update_layout(showlegend=False, height=320, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig1)
    with c2:
        by_type = df.groupby("type")["fill_pct"].mean().round(0).reset_index()
        fig2 = px.bar(by_type, x="type", y="fill_pct", title="Average fill by bin type (%)",
                      color_discrete_sequence=["#1B7F4B"])
        fig2.update_layout(height=320, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig2)
    st.dataframe(df.sort_values("hours_to_full")[
        ["bin_id", "name", "type", "size", "fill_pct", "eta_text", "open_reports", "status"]],
        hide_index=True)
with tab5:
    meta = load_meta()
    if st.button("Retrain model now"):
        with st.spinner("Training on the latest readings..."):
            train()
        st.rerun()
    if not meta:
        st.info("No model yet. Press the button above, or run: python -m ml.forecast --train")
    else:
        a, b, c = st.columns(3)
        a.metric("Model", meta["model_type"])
        if "mae_model" in meta:
            b.metric("Error: ML model", f"{meta['mae_model']:.2f} %/h",
                     delta=f"{meta['mae_model'] - meta['mae_baseline']:.2f} vs baseline",
                     delta_color="inverse")
            c.metric("Error: baseline", f"{meta['mae_baseline']:.2f} %/h")
        st.caption(f"Trained {meta['trained_at']} on {meta['n_train']} bin-hours from "
                   f"{meta['n_bins']} bins. Errors are measured on the last 5 days of simulated data.")
        imp = pd.DataFrame({"feature": list(meta["feature_importance"]),
                            "importance": list(meta["feature_importance"].values())}
                           ).sort_values("importance")
        fig = px.bar(imp, x="importance", y="feature", orientation="h",
                     title="What the model relies on")
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig)

        names = dict(zip(df["bin_id"], df["name"]))
        pick_bin = st.selectbox("Bin", df["bin_id"].tolist(), key="profile_bin",
                                format_func=lambda i: f"{names[i]} ({i})")
        row = df[df["bin_id"] == pick_bin].iloc[0].to_dict()
        prof = pd.DataFrame({"hour": range(24),
                             "Weekday": hourly_profile(row, 1),
                             "Weekend": hourly_profile(row, 6)}
                            ).melt("hour", var_name="day", value_name="gain")
        fig2 = px.line(prof, x="hour", y="gain", color="day",
                       title="Predicted fill gained per hour (%)")
        fig2.update_layout(height=320, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig2)
with tab6:
    pending = sb.pending_list()
    st.subheader(f"Waiting for review ({len(pending)})")
    if not pending:
        st.info("No creations are waiting for review.")
    for s in pending:
        sid = s["id"]
        with st.container(border=True):
            st.markdown(f"**{s['idea_title']}**")
            st.caption(f"By {s['user_name']} ({s['hostel_or_dept'] or 'no hostel or department'}) "
                       f"| {ago(s['created_at'])}")
            st.write(f"**Waste used:** {s['materials']}")
            if s["description"]:
                st.write(s["description"])
            p1, p2 = st.columns(2)
            p1.image(rp.photo_abs(s["process_photo_path"]), caption="Photo 1: waste item or work in progress")
            p2.image(rp.photo_abs(s["photo_path"]), caption="Photo 2: finished product")
            st.info(f"Code check: photo 2 should show the code {s['daily_code']} written on paper "
                    f"(the code of the day it was submitted).")
            st.caption(f"This student: {s['user_approved']} approved, {s['user_rejected']} rejected, "
                       f"{s['user_week']} shared in the last 7 days.")
            similar = sb.similar_to(sid)
            if similar:
                st.warning("Similar photos found: " + ", ".join(
                    f"'{x['title']}' (difference {x['distance']} of 64)" for x in similar))
            reason = st.text_input("Reason (needed to reject)", key=f"rej_{sid}", max_chars=200)
            b1, b2, b3, b4 = st.columns(4)
            action = None
            if b1.button("Approve (+30)", key=f"ap_{sid}", type="primary"):
                action = sb.approve(sid, admin["id"])
            if b2.button("Approve as creative (+40)", key=f"apc_{sid}"):
                action = sb.approve(sid, admin["id"], creative=True)
            if b3.button("Reject", key=f"rj_{sid}"):
                action = sb.reject(sid, admin["id"], reason)
            if b4.button("Reject as fake (-20)", key=f"rf_{sid}"):
                action = sb.reject(sid, admin["id"], reason, fake=True)
            if action:
                ok, msg = action
                if ok:
                    st.session_state["admin_flash"] = msg
                    st.rerun()
                else:
                    st.error(msg)

    flagged = sb.flagged_list()
    st.subheader(f"Flagged by students ({len(flagged)})")
    if not flagged:
        st.caption("Nothing flagged.")
    for s in flagged:
        sid = s["id"]
        with st.container(border=True):
            st.markdown(f"**{s['idea_title']}** by {s['user_name']}")
            st.caption(f"Flagged by {s['flag_count']} students: {s['flag_reasons'] or 'no reasons given'}")
            f1, f2 = st.columns(2)
            f1.image(rp.photo_abs(s["process_photo_path"]), caption="Photo 1")
            f2.image(rp.photo_abs(s["photo_path"]), caption="Photo 2")
            note = st.text_input("Reason (needed to withdraw approval)", key=f"fl_note_{sid}",
                                 max_chars=200)
            k1, k2 = st.columns(2)
            action = None
            if k1.button("Keep approved", key=f"keep_{sid}"):
                action = sb.resolve_flag(sid, admin["id"], False)
            if k2.button("Withdraw approval (points taken back)", key=f"wd_{sid}"):
                action = sb.resolve_flag(sid, admin["id"], True, note)
            if action:
                ok, msg = action
                if ok:
                    st.session_state["admin_flash"] = msg
                    st.rerun()
                else:
                    st.error(msg)