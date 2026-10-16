
import streamlit as st
from services.bins import top_alerts

ICON = {
    "critical": "🔴",
    "soon": "🟠",
    "watch": "🟡",
}


def alert_level(r):
    if r["fill_pct"] >= 90 or r["hours_to_full"] <= 2:
        return "critical"
    if r["hours_to_full"] <= 6:
        return "soon"
    return "watch"


def render_alerts(n=5, compact=False):
    alerts = top_alerts(n)

    if alerts.empty:
        st.success(
            "No bin is expected to fill in the next 24 hours."
        )
        return

    for _, r in alerts.iterrows():
        lvl = alert_level(r)
        text = (
            f"{ICON[lvl]} **{r['name']}** ({r['type']}): "
            f"{r['fill_pct']:.0f}% full, {r['eta_text']}"
        )

        if compact:
            st.markdown(text)
        elif lvl == "critical":
            st.error(text)
        elif lvl == "soon":
            st.warning(text)
        else:
            st.info(text)
