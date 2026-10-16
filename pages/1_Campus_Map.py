
import streamlit as st

from services.auth import require_login, sidebar_user
from services.bins import get_all_bins

st.set_page_config(page_title="Campus Map", layout="wide")

require_login()
sidebar_user()

st.title("Campus Map")

df = get_all_bins()
st.success(f"{len(df)} bins loaded.")

st.dataframe(
    df[
        [
            "bin_id", "name", "type", "size",
            "fill_pct", "eta_text"
        ]
    ],
    hide_index=True
)
