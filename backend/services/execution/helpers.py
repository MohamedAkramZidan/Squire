import logging
from datetime import date, datetime, time
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy.orm import Session

from services import embedder
from config.settings import settings
from .status_mapper import map_status

logger = logging.getLogger(__name__)

TITLE_MATCH_THRESHOLD = 0.50
UPDATE_SEARCH_FIELDS = {"TITLE", "PERSON", "LOCATION"}
FUZZY_TITLE_THRESHOLD = 0.72

def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def clean_title(value: Any, model: type | None = None) -> str | None:
    title = clean_text(value)
    if not title:
        return None

    object_words = ["task", "meeting", "progress", "note"]
    if model is not None:
        object_words.insert(0, model.__name__.lower())

    lowered = title.lower()
    for word in object_words:
        prefix = f"{word} "
        if lowered.startswith(prefix):
            return title[len(prefix):].strip() or title

    return title


def normalize_for_match(value: Any) -> str:
    text = (clean_text(value) or "").lower()
    return "".join(ch for ch in text if ch.isalnum() or ch.isspace()).strip()


def clean_status(value: Any, object_type: str) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    mapped, score, method = map_status(text, object_type)
    if mapped:
        return mapped
    return text.lower().replace(" ", "_")


def clean_progress_status(value: Any) -> str | None:
    return clean_status(value, "PROGRESS")

def parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    text = clean_text(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def parse_time(value: Any) -> time | None:
    if isinstance(value, time):
        return value
    text = clean_text(value)
    if not text:
        return None
    try:
        return time.fromisoformat(text)
    except ValueError:
        return None

def parse_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def fallback_title(processed: dict) -> str:
    text = clean_text(processed.get("text")) or clean_text(processed.get("utterance")) or "Untitled"
    return text[:50]

def serialize(row: Any) -> dict:
    out = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        if isinstance(value, (date, datetime, time)):
            value = value.isoformat()
        elif column.name == "embedding" and value is not None:
            value = {"dimensions": len(value)}
        out[column.name] = value
    return out


def serialize_values(values: dict) -> dict:
    out = {}
    for key, value in values.items():
        if isinstance(value, (date, datetime, time)):
            value = value.isoformat()
        out[key] = value
    return out

def find_matches(
    db: Session,
    model: type,
    date_field: str | None,
    time_field: str | None,
    fields: dict,
    user_id: int,
    action: str = "GET",
    processed: dict | None = None,
) -> list:
    query = db.query(model).filter(model.user_id == user_id)
    target_id = fields.get("TARGET_ID")
    if target_id is not None:
        row = query.filter(model.id == target_id).first()
        return [row] if row else []

    title = clean_title(fields.get("TITLE"), model)
    raw_title = clean_text(fields.get("TITLE")) 

    if model.__tablename__ == "notes":
        search_text = processed.get("text", "") if processed else ""
        if search_text:
            candidates = vector_title_matches(db, model, search_text, user_id)
        else:
            candidates = query.order_by(model.created_at.desc()).limit(20).all()
    elif title:
        if hasattr(model, "embedding"):
            search_phrase = raw_title or title
            candidates = vector_title_matches(db, model, search_phrase, user_id)
        else:
            ilike_rows = query.filter(model.title.ilike(f"%{title}%")).all()
            candidates = [r for r in ilike_rows]
            if not candidates:
                candidates = fuzzy_title_matches(query, title)
    else:
        candidates = query.order_by(model.created_at.desc()).limit(20).all()

    return [
        r for r in candidates
        if passes_filters(r, date_field, time_field, fields, action)
    ]


def vector_title_matches(db: Session, model: type, title: str, user_id: int) -> list:
    if not hasattr(model, "embedding"):
        return []

    logger.info("Vector search: query='%s', threshold=%.2f", title, settings.vector_distance_threshold)

    try:
        query_vec = embedder.embed(title)
    except Exception:
        logger.warning("Failed to generate embedding for query: '%s'", title)
        return []

    from sqlalchemy import Float
    try:
        distance = model.embedding.op("<=>", return_type=Float())(query_vec)
        rows = (
            db.query(model)
            .filter(model.user_id == user_id)
            .filter(model.embedding.isnot(None))
            .filter(distance <= settings.vector_distance_threshold)
            .order_by(distance)
            .limit(3)
            .all()
        )
        logger.info("Vector search found %d results for '%s'", len(rows), title)
    except Exception as exc:
        logger.warning("Vector search failed: %s", exc)
        db.rollback()
        rows = []

    return rows


def fuzzy_title_matches(query: Any, title: str) -> list:
    rows = query.order_by(query.column_descriptions[0]["entity"].created_at.desc()).limit(50).all()
    scored = []
    normalized_title = normalize_for_match(title)
    for row in rows:
        row_title = normalize_for_match(getattr(row, "title", ""))
        score = SequenceMatcher(None, normalized_title, row_title).ratio()
        if score >= FUZZY_TITLE_THRESHOLD:
            scored.append((score, row))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [row for _, row in scored[:3]]


def passes_filters(
    row: Any,
    date_field: str | None,
    time_field: str | None,
    fields: dict,
    action: str,
) -> bool:
    raw_status = fields.get("STATUS")
    if raw_status and hasattr(row, "status"):
        object_type = type(row).__name__.upper()
        mapped_status = clean_status(raw_status, object_type)
        row_status = row.status.value if hasattr(row.status, "value") else str(row.status)
        if mapped_status != row_status:
            return False

    date_val = parse_date(fields.get("DATE"))
    if date_val:
        if date_field and getattr(row, date_field, None) != date_val:
            return False

    time_val = parse_time(fields.get("TIME"))
    if time_val:
        if time_field and getattr(row, time_field, None) != time_val:
            return False

    person = clean_text(fields.get("PERSON"))
    if person and hasattr(row, "person"):
        row_person = getattr(row, "person") or ""
        if person.lower() not in row_person.lower():
            return False

    location = clean_text(fields.get("LOCATION"))
    if location and hasattr(row, "location"):
        row_location = getattr(row, "location") or ""
        if location.lower() not in row_location.lower():
            return False

    return True


def search_fields_for_update(fields: dict) -> dict:
    result = {
        key: value
        for key, value in fields.items()
        if key in UPDATE_SEARCH_FIELDS and clean_text(value)
    }
    if "TARGET_ID" in fields:
        result["TARGET_ID"] = fields["TARGET_ID"]
    return result

def generate_embedding(text: str) -> list[float] | None:
    if not text:
        return None
    try:
        return embedder.embed(text)
    except Exception:
        return None

def executed(
    operation: str,
    obj_name: str,
    row: Any,
    message: str | None = None,
    changes: dict | None = None,
) -> dict:
    res = {
        "status": "EXECUTED",
        "operation": operation,
        "object": obj_name,
        "record": serialize(row),
    }
    if message:
        res["message"] = message
    if changes:
        res["changes"] = serialize_values(changes)
    return res


def not_executed(reason: str) -> dict:
    return {
        "status": "NOT_EXECUTED",
        "reason": reason,
    }


def clarify(reason: str, missing: list[str]) -> dict:
    return {
        "status": "CLARIFY",
        "reason": reason,
        "missing": missing,
    }


def ambiguous(obj_name: str, matches: list) -> dict:
    return {
        "status": "CLARIFY",
        "reason": f"multiple {obj_name.lower()} records match",
        "matches": [serialize(row) for row in matches],
    }
