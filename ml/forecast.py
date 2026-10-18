"""Fill-rate forecasting for WasteWise bins.

  python -m ml.forecast --train      train on bin_readings and save the model
"""
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from services.db import get_conn

MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODEL_DIR / "rate_model.joblib"
META_PATH = MODEL_DIR / "rate_meta.json"

TS = "%Y-%m-%d %H:%M:%S"
HORIZON = 72  # hours to look ahead
TYPE_CODE = {"wet": 0, "dry": 1, "recyclable": 2, "ewaste": 3, "hazardous": 4}
SIZE_CODE = {"small": 0, "medium": 1, "large": 2, "bulk": 3}
FEATURES = ["hour", "weekday", "is_weekend", "type_code", "size_code",
            "usage_rate", "capacity", "bin_mean_rate"]


def make_model():
    try:
        from xgboost import XGBRegressor
        return XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05,
                            subsample=0.9, colsample_bytree=0.9, random_state=42)
    except ImportError:
        from sklearn.ensemble import GradientBoostingRegressor
        return GradientBoostingRegressor(n_estimators=200, max_depth=3,
                                         learning_rate=0.05, random_state=42)


# ---------------------------------------------------------------- training data
def load_training_frame():
    """One row per bin per hour: the % fill gained during that hour (cleaning drops removed)."""
    with get_conn() as conn:
        readings = pd.read_sql_query(
            "SELECT bin_id, fill_pct, recorded_at FROM bin_readings", conn,
            parse_dates=["recorded_at"])
        bins = pd.read_sql_query(
            "SELECT bin_id, type, size, capacity_litres, fill_rate_per_hr FROM bins", conn)
    if readings.empty:
        return pd.DataFrame(), bins
    readings = readings.sort_values(["bin_id", "recorded_at"])
    readings["bucket"] = readings["recorded_at"].dt.floor("h")
    hourly = readings.groupby(["bin_id", "bucket"], as_index=False).last()
    hourly = hourly.sort_values(["bin_id", "bucket"])
    g = hourly.groupby("bin_id")
    hourly["prev_fill"] = g["fill_pct"].shift(1)
    hourly["prev_ts"] = g["recorded_at"].shift(1)
    hourly["dt_h"] = (hourly["recorded_at"] - hourly["prev_ts"]).dt.total_seconds() / 3600
    gain = hourly["fill_pct"] - hourly["prev_fill"]
    hourly["rate"] = gain / hourly["dt_h"]
    ok = (hourly["dt_h"].between(0.75, 1.25) & (gain >= 0)
          & (hourly["prev_fill"] < 97) & (hourly["fill_pct"] < 100))
    df = hourly[ok].copy()
    df["hour"] = df["recorded_at"].dt.hour
    df["weekday"] = df["recorded_at"].dt.weekday
    df = df.merge(bins, on="bin_id", how="left")
    return df, bins


def add_features(df, bin_mean):
    df = df.copy()
    df["is_weekend"] = (df["weekday"] >= 5).astype(int)
    df["type_code"] = df["type"].map(TYPE_CODE)
    df["size_code"] = df["size"].map(SIZE_CODE)
    df["usage_rate"] = df["fill_rate_per_hr"]
    df["capacity"] = df["capacity_litres"]
    df["bin_mean_rate"] = df["bin_id"].map(bin_mean).fillna(df["fill_rate_per_hr"])
    return df


def train():
    df, _ = load_training_frame()
    if len(df) < 500:
        print("Not enough history yet. Run:  python -m ml.simulator --backfill-days 28")
        return None
    meta = {}
    cutoff = df["recorded_at"].max() - pd.Timedelta(days=5)
    tr_df, te_df = df[df["recorded_at"] <= cutoff], df[df["recorded_at"] > cutoff]
    if len(tr_df) >= 300 and len(te_df) >= 200:
        bm = tr_df.groupby("bin_id")["rate"].mean().to_dict()
        tr, te = add_features(tr_df, bm), add_features(te_df, bm)
        m = make_model()
        m.fit(tr[FEATURES], tr["rate"])
        pred = np.clip(m.predict(te[FEATURES]), 0, None)
        meta["mae_model"] = float(np.mean(np.abs(pred - te["rate"])))
        meta["mae_baseline"] = float(np.mean(np.abs(te["bin_mean_rate"] - te["rate"])))
        meta["n_test"] = int(len(te))
        print(f"Backtest on the last 5 days ({len(te)} bin-hours):")
        print(f"  baseline (each bin's average rate): MAE {meta['mae_baseline']:.3f} %/h")
        print(f"  ML model                          : MAE {meta['mae_model']:.3f} %/h")
    else:
        print("Not enough data for a backtest; training the final model anyway.")

    bm_all = df.groupby("bin_id")["rate"].mean().to_dict()
    full = add_features(df, bm_all)
    model = make_model()
    model.fit(full[FEATURES], full["rate"])
    meta.update(
        trained_at=datetime.now().strftime(TS),
        n_train=int(len(full)),
        n_bins=int(full["bin_id"].nunique()),
        model_type=type(model).__name__,
        bin_mean_rate={k: float(v) for k, v in bm_all.items()},
        feature_importance=dict(zip(FEATURES, [float(x) for x in model.feature_importances_])),
    )
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    META_PATH.write_text(json.dumps(meta, indent=2))
    print(f"Saved {meta['model_type']} trained on {meta['n_train']} bin-hours "
          f"from {meta['n_bins']} bins -> {MODEL_PATH.name}")
    return meta


# ------------------------------------------------------------------- prediction
_cache = {"mtime": None, "model": None, "meta": None}


def load_model():
    if not MODEL_PATH.exists() or not META_PATH.exists():
        return None, None
    mtime = MODEL_PATH.stat().st_mtime
    if _cache["mtime"] != mtime:
        _cache.update(mtime=mtime, model=joblib.load(MODEL_PATH),
                      meta=json.loads(META_PATH.read_text()))
    return _cache["model"], _cache["meta"]


def load_meta():
    return load_model()[1]


def current_time():
    """Latest reading time (matches the simulator clock); falls back to the real clock."""
    with get_conn() as conn:
        ts = conn.execute("SELECT MAX(recorded_at) FROM bin_readings").fetchone()[0]
    return datetime.strptime(ts, TS) if ts else datetime.now()


def _bin_mean(bins_df, meta):
    base = bins_df["fill_rate_per_hr"].to_numpy(float)
    mm = meta.get("bin_mean_rate", {})
    return base, np.array([mm.get(b, base[i]) for i, b in enumerate(bins_df["bin_id"])])


def predict_rate_matrix(bins_df, start, horizon, model, meta):
    """Expected % gained in each of the next `horizon` hours, shape (n_bins, horizon)."""
    n = len(bins_df)
    times = [start + timedelta(hours=k) for k in range(1, horizon + 1)]
    hour = np.array([t.hour for t in times])
    wd = np.array([t.weekday() for t in times])
    base, bm = _bin_mean(bins_df, meta)
    X = pd.DataFrame({
        "hour": np.tile(hour, n),
        "weekday": np.tile(wd, n),
        "is_weekend": np.tile((wd >= 5).astype(int), n),
        "type_code": np.repeat(bins_df["type"].map(TYPE_CODE).to_numpy(float), horizon),
        "size_code": np.repeat(bins_df["size"].map(SIZE_CODE).to_numpy(float), horizon),
        "usage_rate": np.repeat(base, horizon),
        "capacity": np.repeat(bins_df["capacity_litres"].to_numpy(float), horizon),
        "bin_mean_rate": np.repeat(bm, horizon),
    })[FEATURES]
    return np.clip(model.predict(X), 0, None).reshape(n, horizon)


def _hours_to_full(fill, rates):
    if fill >= 100:
        return 0.0
    cum = fill + np.cumsum(rates)
    hit = np.nonzero(cum >= 100)[0]
    if hit.size:
        i = int(hit[0])
        prev = fill if i == 0 else cum[i - 1]
        return i + (100 - prev) / max(rates[i], 1e-9)
    avg = rates.mean()
    if avg < 0.01:
        return np.nan
    return len(rates) + (100 - cum[-1]) / avg


def predict_hours_to_full(bins_df, horizon=HORIZON):
    """ML time-to-full (hours) for each bin, or None if no trained model exists."""
    model, meta = load_model()
    if model is None or bins_df.empty:
        return None
    now = current_time()
    start = now.replace(minute=0, second=0, microsecond=0)
    elapsed = (now - start).total_seconds() / 3600
    rates = predict_rate_matrix(bins_df, start, horizon, model, meta)
    rates[:, 0] *= (1 - elapsed)
    fills = bins_df["fill_pct"].to_numpy(float)
    return np.array([_hours_to_full(f, r) for f, r in zip(fills, rates)])


def hourly_profile(bin_row, weekday=1):
    """Predicted % gained per hour of the day for one bin (for the admin chart)."""
    model, meta = load_model()
    if model is None:
        return None
    one = pd.DataFrame([bin_row])
    base, bm = _bin_mean(one, meta)
    X = pd.DataFrame({
        "hour": np.arange(24), "weekday": weekday, "is_weekend": int(weekday >= 5),
        "type_code": float(TYPE_CODE.get(bin_row["type"], np.nan)),
        "size_code": float(SIZE_CODE.get(bin_row["size"], np.nan)),
        "usage_rate": base[0], "capacity": float(bin_row["capacity_litres"]),
        "bin_mean_rate": bm[0],
    })[FEATURES]
    return np.clip(model.predict(X), 0, None)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", action="store_true", help="train and save the model")
    a = ap.parse_args()
    if a.train:
        train()
    else:
        ap.print_help()