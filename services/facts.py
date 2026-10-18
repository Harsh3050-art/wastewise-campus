import json
from datetime import date
from pathlib import Path

FACTS_PATH = Path(__file__).resolve().parent.parent / "data" / "facts.json"


def _load():
    try:
        return json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def fact_of_the_day():
    facts = _load()
    return facts[date.today().toordinal() % len(facts)] if facts else None


def fact_for(key):
    """A fact that stays the same for the same key (for example the item name)."""
    facts = _load()
    return facts[sum(map(ord, key or "")) % len(facts)] if facts else None