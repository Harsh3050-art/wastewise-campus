"""Bin fill simulator.

  python -m ml.simulator --backfill-days 28
  python -m ml.simulator --live --interval 10 --step-minutes 10
"""
import argparse
import random
import time
from datetime import datetime, timedelta

from services.db import get_conn

TS = "%Y-%m-%d %H:%M:%S"


def hour_factor(btype, hour):
    # wet bins peak at meal times, other bins during the day
    if btype == "wet":
        base, peaks = 0.4, [(7, 10, 1.8), (12, 15, 1.8), (19, 22, 2.0)]
    else:
        base, peaks = 0.5, [(9, 18, 1.5)]
    for a, b, m in peaks:
        if a <= hour < b:
            return m
    return base


def day_factor(t):
    return 0.8 if t.weekday() >= 5 else 1.0


def step_fill(fill, rate, btype, t, step_h):
    noise = random.uniform(0.7, 1.3)
    inc = rate * hour_factor(btype, t.hour) * day_factor(t) * noise * step_h
    return min(100.0, fill + inc)


def load_bins(conn):
    return [dict(r) for r in conn.execute(
        "SELECT bin_id, type, fill_pct, fill_rate_per_hr FROM bins WHERE active = 1")]


def backfill(days, step_minutes=60):
    random.seed(7)
    step_h = step_minutes / 60
    end = datetime.now().replace(minute=0, second=0, microsecond=0)
    t = end - timedelta(days=days)
    with get_conn() as conn:
        conn.execute("DELETE FROM bin_readings")
        bins = load_bins(conn)
        state = {b["bin_id"]: random.uniform(5, 40) for b in bins}
        last_clean, rows = {}, []
        while t <= end:
            for b in bins:
                bid = b["bin_id"]
                fill = step_fill(state[bid], b["fill_rate_per_hr"], b["type"], t, step_h)
                nearly_full = fill >= 85 and random.random() < 0.35
                morning_round = t.hour == 6 and fill >= 40 and random.random() < 0.6
                if nearly_full or morning_round:
                    fill = random.uniform(0, 6)
                    last_clean[bid] = t
                state[bid] = fill
                rows.append((bid, round(fill, 1), t.strftime(TS)))
            t += timedelta(minutes=step_minutes)
        conn.executemany(
            "INSERT INTO bin_readings (bin_id, fill_pct, recorded_at) VALUES (?,?,?)", rows)
        for b in bins:
            bid = b["bin_id"]
            conn.execute(
                "UPDATE bins SET fill_pct = ?, last_cleaned_at = ? WHERE bin_id = ?",
                (round(state[bid], 1),
                 last_clean[bid].strftime(TS) if bid in last_clean else None, bid))
    above = sum(1 for v in state.values() if v >= 80)
    print(f"Backfill done: {len(rows)} readings over {days} days. "
          f"{above} bins are above 80% right now.")


def live(interval, step_minutes, auto_clean):
    step_h = step_minutes / 60
    with get_conn() as conn:
        last = conn.execute("SELECT MAX(recorded_at) FROM bin_readings").fetchone()[0]
    t = datetime.strptime(last, TS) if last else datetime.now()
    print(f"Live simulation: every {interval}s = {step_minutes} simulated minutes. Ctrl+C to stop.")
    try:
        while True:
            t += timedelta(minutes=step_minutes)
            with get_conn() as conn:
                bins = load_bins(conn)
                rows = []
                for b in bins:
                    fill = step_fill(b["fill_pct"], b["fill_rate_per_hr"], b["type"], t, step_h)
                    if auto_clean and fill >= 95 and random.random() < 0.3:
                        fill = random.uniform(0, 5)
                        conn.execute("UPDATE bins SET last_cleaned_at = ? WHERE bin_id = ?",
                                     (datetime.now().strftime(TS), b["bin_id"]))
                    conn.execute("UPDATE bins SET fill_pct = ? WHERE bin_id = ?",
                                 (round(fill, 1), b["bin_id"]))
                    rows.append((b["bin_id"], round(fill, 1), t.strftime(TS)))
                conn.executemany(
                    "INSERT INTO bin_readings (bin_id, fill_pct, recorded_at) VALUES (?,?,?)", rows)
            print(f"[{t:%a %H:%M}] updated {len(rows)} bins")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Simulator stopped.")

def advance(hours, step_minutes=10, auto_clean=False):
    """Fast-forward the simulation by `hours` without waiting."""
    step_h = step_minutes / 60
    ticks = max(1, int(hours * 60 // step_minutes))
    with get_conn() as conn:
        last = conn.execute("SELECT MAX(recorded_at) FROM bin_readings").fetchone()[0]
        t = datetime.strptime(last, TS) if last else datetime.now()
        bins = load_bins(conn)
        fills = {b["bin_id"]: b["fill_pct"] for b in bins}
        rows = []
        for _ in range(ticks):
            t += timedelta(minutes=step_minutes)
            for b in bins:
                bid = b["bin_id"]
                fill = step_fill(fills[bid], b["fill_rate_per_hr"], b["type"], t, step_h)
                if auto_clean and fill >= 95 and random.random() < 0.3:
                    fill = random.uniform(0, 5)
                fills[bid] = fill
                rows.append((bid, round(fill, 1), t.strftime(TS)))
        for bid, fill in fills.items():
            conn.execute("UPDATE bins SET fill_pct = ? WHERE bin_id = ?", (round(fill, 1), bid))
        conn.executemany("INSERT INTO bin_readings (bin_id, fill_pct, recorded_at) VALUES (?,?,?)", rows)
    print(f"Advanced {ticks * step_minutes / 60:.1f} hours ({ticks} steps). "
          f"Simulated time is now {t:%a %d %b %H:%M}.")
def main():
    p = argparse.ArgumentParser(description="WasteWise bin fill simulator")
    p.add_argument("--backfill-days", type=int, help="generate N days of history")
    p.add_argument("--advance-hours", type=float, help="fast-forward the simulation by N hours instantly")
    p.add_argument("--live", action="store_true", help="keep updating until Ctrl+C")
    p.add_argument("--interval", type=float, default=10, help="real seconds between updates")
    p.add_argument("--step-minutes", type=int, default=10, help="simulated minutes per update")
    p.add_argument("--auto-clean", action="store_true", help="simulate a cleaning crew")
    a = p.parse_args()
    if a.backfill_days:
        backfill(a.backfill_days)
    if a.advance_hours:
        advance(a.advance_hours, a.step_minutes, a.auto_clean)
    if a.live:
        live(a.interval, a.step_minutes, a.auto_clean)
    if not (a.backfill_days or a.advance_hours or a.live):
        p.print_help()


if __name__ == "__main__":
    main()