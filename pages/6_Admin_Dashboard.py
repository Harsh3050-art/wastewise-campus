import plotly.express as px
import streamlit as st
from services.auth import require_admin, sidebar_user
from services.alerts import render_alerts
from services.stats import admin_kpis

st.set_page_config(page_title="Admin Dashboard", layout="wide")
require_admin()
sidebar_user()

df, k = admin_kpis()

st.title("Admin Dashboard")

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

st.subheader("Campus overview")
c1, c2 = st.columns(2)
with c1:
    status = df["status"].value_counts().reindex(["green", "yellow", "red"], fill_value=0).reset_index()
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

st.subheader("All bins by time to full")
st.dataframe(df.sort_values("hours_to_full")[
    ["bin_id", "name", "type", "size", "fill_pct", "eta_text", "status"]], hide_index=True)
st.info("Mark as cleaned and report-based ranking come on Day 4.")