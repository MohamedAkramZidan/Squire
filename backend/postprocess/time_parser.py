import re
from datetime import datetime, timedelta

_NAMED_TIMES = {
    "noon": "12:00",
    "midday": "12:00",
    "midnight": "00:00",
    "morning": "09:00",
    "afternoon": "14:00",
    "evening": "18:00",
    "night": "21:00",
}

def resolve_time(raw: str) -> str | None:
    text = raw.strip().lower()

    if text in _NAMED_TIMES:
        return _NAMED_TIMES[text]

    m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
    if not m:
        return None

    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    period = m.group(3)

    if period == "pm" and hour != 12:
        hour += 12
    elif period == "am" and hour == 12:
        hour = 0

    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return f"{hour:02d}:{minute:02d}"

    return None