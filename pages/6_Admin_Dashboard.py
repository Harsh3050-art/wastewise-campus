
import streamlit as st

from services.auth import require_admin, sidebar_user
from services.alerts import render_alerts
from services.bins import get_all_bins

st.set_page_config(
    page_title="Admin Dashboard",
    layout="wide"
)

require_admin()
sidebar_user()

st.title("Admin Dashboard")
st.subheader("Top 5 bins about to fill")

render_alerts(5)

st.subheader("All bins by time to full")

df = get_all_bins().sort_values("hours_to_full")

st.dataframe(
    df[
        [
            "bin_id", "name", "type", "size",
            "fill_pct", "eta_text", "status"
        ]
    ],
    hide_index=True
)

st.info(
    "Mark as cleaned and report-based ranking come on Day 4."
)
