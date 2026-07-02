import re
from datetime import datetime

from .normalizers import NORMALIZERS
from .validators import validate
from .date_parser import resolve_date

def process(raw, reference_date=None):

    reference_date = reference_date or datetime.now()

    action = raw.get("action")
    obj = raw.get("object")

    fields = {}
    best_conf = {}

    for entity in raw.get("entities", []):

        tag = entity.get("type")
        value = entity.get("value")
        conf = entity.get("confidence") or 0.0

        if not tag or not value:
            continue

        if conf < 0.50:
            continue

        if tag in fields and conf <= best_conf.get(tag, -1.0):
            continue

        best_conf[tag] = conf

        fn = NORMALIZERS.get(tag)

        normalized = (
            fn(value, reference_date)
            if fn
            else value
        )

        fields[tag] = normalized

    text = raw.get("text") or raw.get("utterance") or ""
    _apply_date_fallback(fields, text, reference_date)

    missing = validate(action, obj, fields)

    return {
        **raw,
        "fields": fields,
        "missing": missing,
        "ok": len(missing) == 0,
    }


def _apply_date_fallback(fields: dict, text: str, reference_date: datetime) -> None:
    if fields.get("DATE") or not text:
        return

    lowered = text.lower()
    patterns = [
        r"\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        r"\b(today|tomorrow|yesterday)\b",
        r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{1,2}/\d{1,2}/\d{4}\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, lowered)
        if not match:
            continue
        resolved = resolve_date(match.group(0), reference_date)
        if resolved:
            fields["DATE"] = resolved
            return
