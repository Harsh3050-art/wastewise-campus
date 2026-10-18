"""Compare ML time-to-full with a constant-rate estimate, against the simulator's true pattern.

  python -m ml.validate_forecast
"""
from datetime import timedelta

import numpy as np

from ml.forecast import current_time
from ml.simulator import day_factor, hour_factor
from services.bins import get_all_bins


def true_hours(r, now):
    fill = r["fill_pct"]
    start = now.replace(minute=0, second=0, microsecond=0)
    elapsed = (now - start).total_seconds() / 3600
    for k in range(1, 400):
        t = start + timedelta(hours=k)
        inc = r["fill_rate_per_hr"] * hour_factor(r["type"], t.hour) * day_factor(t)
        if k == 1:
            inc *= 1 - elapsed
        if fill + inc >= 100:
            return k - 1 + (100 - fill) / inc
        fill += inc
    return np.nan


df = get_all_bins()
if df["forecast_source"].iloc[0] != "ML model":
    raise SystemExit("No trained model yet. Run: python -m ml.forecast --train")
now = current_time()
df["truth"] = df.apply(lambda r: true_hours(r, now), axis=1)
sel = df[(df["truth"] < 72) & (df["fill_pct"] >= 30)]
print(f"Bins compared: {len(sel)} (fill 30% or more, full within 72 h)")
print(f"Average error, ML model      : {(sel['hours_to_full'] - sel['truth']).abs().mean():.2f} hours")
print(f"Average error, constant rate : {(sel['hours_simple'] - sel['truth']).abs().mean():.2f} hours")