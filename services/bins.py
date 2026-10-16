
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from services.db import get_conn


def eta_phrase(h):
    if h is None or pd.isna(h):
        return "no estimate"
    if h <= 0:
        return "full now"

    total = int(round(h * 60))
    days, rem = divmod(total, 1440)
    hrs, mins = divmod(rem, 60)

    if days:
        return f"full in {days}d {hrs}h"
    if hrs:
        return f"full in {hrs}h {mins}m"
    return f"full in {mins}m"


def status_of(pct):
    return "green" if pct < 50 else "yellow" if pct < 80 else "red"


def add_forecast(df):
    df = df.copy()

    def hours(r):
        if r["fill_pct"] >= 100:
            return 0.0
        if r["fill_rate_per_hr"] <= 0:
            return np.nan
        return (100 - r["fill_pct"]) / r["fill_rate_per_hr"]

    df["hours_to_full"] = (
        df.apply(hours, axis=1) if len(df) else pd.Series(dtype=float)
    )

    now = datetime.now()
    df["full_at"] = df["hours_to_full"].apply(
        lambda h: pd.NaT if pd.isna(h)
        else now + timedelta(hours=h)
    )
    df["eta_text"] = df["hours_to_full"].apply(eta_phrase)
    df["status"] = df["fill_pct"].apply(status_of)

    return df


def get_all_bins() -> pd.DataFrame:
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM bins WHERE active = 1", conn
        )
    return add_forecast(df)


def top_alerts(n=5, within_hours=24):
    df = get_all_bins()
    df = df[
        df["hours_to_full"].notna()
        & (df["hours_to_full"] <= within_hours)
    ]
    return df.sort_values("hours_to_full").head(n)
