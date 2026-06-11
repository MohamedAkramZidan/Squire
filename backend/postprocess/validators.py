from .config import REQUIRED

def validate(action, obj, fields):

    required = REQUIRED.get((action, obj), [])

    missing = [
        field
        for field in required
        if field not in fields
    ]

    return missing