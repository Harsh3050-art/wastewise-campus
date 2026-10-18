import plotly.express as px
import streamlit as st
import pandas as pd
from ml.forecast import load_meta, hourly_profile, train

from services import reports as rp
from services.alerts import render_alerts
from services.auth import require_admin, sidebar_user, current_user
from services.cleaning import mark_cleaned, avg_response_hours, clean_history
from services.stats import admin_kpis
from services.timeutil import ago

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

st.subheader("Top 5 bins about to fill")
render_alerts(5)

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Priority list and cleaning", "Open reports", "Cleaning history", "Overview", "Forecast model"])

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
    items = rp.open_reports_all()
    if not items:
        st.info("No open reports right now.")
    for x in items:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.write(f"**{x['bin_name']}** ({x['bin_id']}): {x['tag']}")
                if x["comment"]:
                    st.write(x["comment"])
                st.caption(f"By {x['user_name']} | {ago(x['created_at'])} | {x['upvotes']} me too")
            with c2:
                if x["photo_path"]:
                    st.image(rp.photo_abs(x["photo_path"]), width=120)
            if st.button("Dismiss (not valid)", key=f"dismiss_{x['id']}"):
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