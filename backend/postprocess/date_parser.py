import re
from datetime import datetime, timedelta

_RELATIVE = {
    "today": 0,
    "tomorrow": 1,
    "yesterday": -1,
}

_WEEKDAYS = [
    "monday", "tuesday", "wednesday",
    "thursday", "friday", "saturday", "sunday"
]

def resolve_date(raw: str, ref: datetime = None) -> str | None:
    ref = ref or datetime.utcnow()
    text = raw.strip().lower()

    if text in _RELATIVE:
        return (ref + timedelta(days=_RELATIVE[text])).strftime("%Y-%m-%d")

    for i, day in enumerate(_WEEKDAYS):
        if text == day or f"next {day}" in text:
            days_ahead = (i - ref.weekday()) % 7 or 7
            return (ref + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    patterns = [
        (r"(\d{4})-(\d{2})-(\d{2})", lambda m: text),
        (r"(\d{1,2})/(\d{1,2})/(\d{4})",
         lambda m: f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}")
    ]

    for pattern, handler in patterns:
        m = re.fullmatch(pattern, text)
        if m:
            return handler(m)

    months = [
        "january","february","march","april","may","june",
        "july","august","september","october","november","december"
    ]

    for i, month in enumerate(months, 1):
        m = re.search(rf"(\d{{1,2}})\s+{month}\s+(\d{{4}})", text)
        if m:
            return f"{m.group(2)}-{i:02d}-{int(m.group(1)):02d}"

        m = re.search(rf"{month}\s+(\d{{1,2}})\s+(\d{{4}})", text)
        if m:
            return f"{m.group(2)}-{i:02d}-{int(m.group(1)):02d}"

    return None