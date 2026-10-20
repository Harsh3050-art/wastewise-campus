import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from services.db import get_conn

ALL_BINS_SQL = """
SELECT b.*, COALESCE(r.cnt, 0) AS open_reports
FROM bins b
LEFT JOIN (SELECT bin_id, COUNT(*) AS cnt FROM reports
           WHERE status = 'open' GROUP BY bin_id) r ON r.bin_id = b.bin_id
WHERE b.active = 1
"""


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


def _ml_hours(df):
    """Time to full from the trained ML model, or None if it is not available."""
    try:
        from ml.forecast import predict_hours_to_full
        return predict_hours_to_full(df)
    except Exception as e:  # never break the app because of the model
        print("ML forecast unavailable, using constant rate:", e)
        return None


def add_forecast(df):
    if df.empty:
        return df.assign(hours_to_full=[], hours_simple=[], forecast_source=[], full_at=[],
                         eta_text=[], status=[], open_reports=[], priority=[])
    df = df.copy()
    if "open_reports" not in df.columns:
        df["open_reports"] = 0

    def simple(r):
        if r["fill_pct"] >= 100:
            return 0.0
        if r["fill_rate_per_hr"] <= 0:
            return np.nan
        return (100 - r["fill_pct"]) / r["fill_rate_per_hr"]

    df["hours_simple"] = df.apply(simple, axis=1)
    ml = _ml_hours(df)
    if ml is not None:
        df["hours_to_full"] = ml
        df["forecast_source"] = "ML model"
    else:
        df["hours_to_full"] = df["hours_simple"]
        df["forecast_source"] = "constant rate"

    now = datetime.now()
    df["full_at"] = df["hours_to_full"].apply(
        lambda h: pd.NaT if pd.isna(h) else now + timedelta(hours=h))
    df["eta_text"] = df["hours_to_full"].apply(eta_phrase)
    df["status"] = df["fill_pct"].apply(status_of)

    h = df["hours_to_full"].fillna(999)
    urgency = (1 - h / 24).clip(lower=0, upper=1) * 100
    report_score = (df["open_reports"] * 20).clip(upper=100)
    df["priority"] = (0.5 * urgency + 0.3 * df["fill_pct"] + 0.2 * report_score).round(1)
    return df


def get_all_bins() -> pd.DataFrame:
    with get_conn() as conn:
        df = pd.read_sql_query(ALL_BINS_SQL, conn)
    return add_forecast(df)


def top_alerts(n=5, within_hours=24, min_fill=30):
    """Bins that are filling soon. Nearly empty bins are not alerts."""
    df = get_all_bins()
    df = df[df["hours_to_full"].notna() & (df["hours_to_full"] <= within_hours)
            & (df["fill_pct"] >= min_fill)]
    return df.sort_values("hours_to_full").head(n)


def get_readings(bin_id, limit=96):
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT fill_pct, recorded_at FROM bin_readings "
            "WHERE bin_id = ? ORDER BY recorded_at DESC LIMIT ?",
            conn, params=(bin_id, limit))
    df["recorded_at"] = pd.to_datetime(df["recorded_at"])
    return df.sort_values("recorded_at")