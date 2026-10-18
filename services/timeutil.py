
from datetime import datetime, timezone

FMT = "%Y-%m-%d %H:%M:%S"


def _parse(ts):
    return datetime.strptime(ts, FMT).replace(tzinfo=timezone.utc)


def ago(ts):
    if not ts:
        return ""

    secs = int(
        (datetime.now(timezone.utc) - _parse(ts)).total_seconds()
    )

    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{secs // 60} min ago"
    if secs < 86400:
        return f"{secs // 3600} h ago"

    return f"{secs // 86400} d ago"


def local_str(ts):
    if not ts:
        return ""

    return _parse(ts).astimezone().strftime("%d %b %Y, %H:%M")
