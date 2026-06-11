from datetime import datetime

from .normalizers import NORMALIZERS
from .validators import validate


def process(raw, reference_date=None):

    reference_date = reference_date or datetime.now()

    action = raw.get("action")
    obj = raw.get("object")

    fields = {}

    for entity in raw.get("entities", []):

        tag = entity.get("type")
        value = entity.get("value")

        if not tag or not value:
            continue

        fn = NORMALIZERS.get(tag)

        normalized = (
            fn(value, reference_date)
            if fn
            else value
        )

        fields[tag] = normalized

    missing = validate(action, obj, fields)

    return {
        **raw,
        "fields": fields,
        "missing": missing,
        "ok": len(missing) == 0,
    }