from services import submissions as sb
from services.bins import get_all_bins
from services.cleaning import avg_response_hours
from services.db import get_conn
from services.timeutil import ago

TYPE_NAME = {"wet": "Wet", "dry": "Dry", "recyclable": "Recyclable", "ewaste": "E-waste",
             "hazardous": "Hazardous"}


def daily_brief():
    """A short plain-language summary for the waste team, built from the live numbers."""
    df = get_all_bins()
    if df.empty:
        return ["No bins are set up yet."]
    lines = []
    red = int((df["fill_pct"] >= 80).sum())
    soon = int(((df["hours_to_full"] <= 6) & (df["fill_pct"] >= 30)).sum())
    lines.append(f"{red} of {len(df)} bins are above 80% full, and {soon} more are expected "
                 f"to be full within 6 hours.")
    top = df.sort_values("priority", ascending=False).head(3)
    if top.iloc[0]["priority"] > 0:
        parts = [f"{r['name']} ({r['fill_pct']:.0f}%, {r['eta_text']})" for _, r in top.iterrows()]
        lines.append("Clean these first: " + "; ".join(parts) + ".")
    by_type = df.groupby("type")["fill_pct"].mean().sort_values(ascending=False)
    lines.append(f"{TYPE_NAME.get(by_type.index[0], by_type.index[0])} bins are the fullest on "
                 f"average ({by_type.iloc[0]:.0f}%).")
    with get_conn() as conn:
        open_n = conn.execute("SELECT COUNT(*) FROM reports WHERE status = 'open'").fetchone()[0]
        oldest = conn.execute("SELECT MIN(created_at) FROM reports WHERE status = 'open'").fetchone()[0]
        cleaned = conn.execute("SELECT COUNT(*) FROM clean_log "
                               "WHERE date(cleaned_at) = date('now')").fetchone()[0]
    if open_n:
        lines.append(f"{open_n} open report(s) from students. The oldest was sent {ago(oldest)}.")
    else:
        lines.append("There are no open reports from students.")
    avg = avg_response_hours()
    tail = f"{cleaned} bin(s) cleaned today."
    lines.append((f"Average time from report to cleaning so far: {avg:.1f} hours. " if avg is not None else "") + tail)
    pending, flagged = sb.counts()
    if pending or flagged:
        lines.append(f"{pending} creation(s) are waiting for review and {flagged} flagged by students.")
    return lines