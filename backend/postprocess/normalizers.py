from .date_parser import resolve_date
from .time_parser import resolve_time

def normalize_name(raw: str) -> str:
    text = raw.strip()
    for p in ["mr.", "mrs.", "ms.", "dr.", "prof."]:
        if text.lower().startswith(p):
            text = text[len(p):].strip()
    return " ".join(w.capitalize() for w in text.split())

def normalize_location(raw: str) -> str:
    return " ".join(w.capitalize() for w in raw.strip().split())

NORMALIZERS = {
    "DATE": lambda v, r: resolve_date(v, r),
    "TIME": lambda v, r: resolve_time(v),
    "PERSON": lambda v, r: normalize_name(v),
    "LOCATION": lambda v, r: normalize_location(v),
}