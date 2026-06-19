from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from database.crud.meetings import meeting as meeting_crud
from database.crud.notes import note as note_crud
from database.crud.progress import progress as progress_crud
from database.crud.tasks import task as task_crud
from database.models import Meeting, Note, Progress, Task, User
from schemas.meetings import MeetingCreate, MeetingUpdate
from schemas.notes import NoteCreate, NoteUpdate
from schemas.progress import ProgressCreate, ProgressUpdate
from schemas.tasks import TaskCreate, TaskUpdate
from services import embedder


class ObjectConfig:
    def __init__(
        self,
        model: type,
        crud: Any,
        create_schema: type[BaseModel],
        update_schema: type[BaseModel],
        date_field: str | None = None,
        time_field: str | None = None,
    ):
        self.model = model
        self.crud = crud
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.date_field = date_field
        self.time_field = time_field


OBJECTS = {
    "TASK": ObjectConfig(Task, task_crud, TaskCreate, TaskUpdate, "task_date", "task_time"),
    "MEETING": ObjectConfig(
        Meeting,
        meeting_crud,
        MeetingCreate,
        MeetingUpdate,
        "meeting_date",
        "meeting_time",
    ),
    "NOTE": ObjectConfig(Note, note_crud, NoteCreate, NoteUpdate),
    "PROGRESS": ObjectConfig(Progress, progress_crud, ProgressCreate, ProgressUpdate),
}


def execute_intent(db: Session, processed: dict, user_id: int | None) -> dict:
    if user_id is None:
        return _not_executed("missing user_id")

    if not db.get(User, user_id):
        return _not_executed("user not found")

    action = processed.get("action")
    obj_name = processed.get("object")
    fields = processed.get("fields", {})

    config = OBJECTS.get(obj_name)
    if not config:
        return _not_executed(f"unsupported object: {obj_name}")

    if action == "ADD":
        return _add(db, config, obj_name, fields, user_id, processed)
    if action == "GET":
        return _get(db, config, obj_name, fields, user_id)
    if action == "UPDATE":
        return _update(db, config, obj_name, fields, user_id)
    if action == "DELETE":
        return _delete(db, config, obj_name, fields, user_id)

    return _not_executed(f"unsupported action: {action}")


def _add(
    db: Session,
    config: ObjectConfig,
    obj_name: str,
    fields: dict,
    user_id: int,
    processed: dict,
) -> dict:
    data = _payload_for_object(config, obj_name, fields, user_id, processed)
    missing = _missing_required_for_create(obj_name, data)
    if missing:
        return _clarify(f"missing required fields for {obj_name.lower()}: {missing}", missing)

    try:
        payload = config.create_schema(**data)
    except ValidationError as exc:
        return _not_executed(f"invalid create payload: {exc.errors()}")

    created = config.crud.create(db, payload)

    # embed the title and persist it
    _update_embedding(db, created)

    return _executed("created", obj_name, created)


def _get(db: Session, config: ObjectConfig, obj_name: str, fields: dict, user_id: int) -> dict:
    matches = _find_matches(db, config, fields, user_id)
    return {
        "status": "EXECUTED",
        "operation": "get",
        "object": obj_name,
        "count": len(matches),
        "records": [_serialize(row) for row in matches],
    }


def _update(db: Session, config: ObjectConfig, obj_name: str, fields: dict, user_id: int) -> dict:
    matches = _find_matches(db, config, fields, user_id)
    if not matches:
        return _not_executed(f"{obj_name.lower()} not found")
    if len(matches) > 1:
        return _ambiguous(obj_name, matches)

    update_data = _update_payload_for_object(config, obj_name, fields)
    if not update_data:
        return _clarify(f"no update fields provided for {obj_name.lower()}", ["STATUS", "DATE", "TIME"])

    try:
        payload = config.update_schema(**update_data)
    except ValidationError as exc:
        return _not_executed(f"invalid update payload: {exc.errors()}")

    updated = config.crud.update(db, matches[0], payload)

    # if title changed, re-embed
    if "title" in update_data:
        _update_embedding(db, updated)

    return _executed("updated", obj_name, updated)


def _delete(db: Session, config: ObjectConfig, obj_name: str, fields: dict, user_id: int) -> dict:
    matches = _find_matches(db, config, fields, user_id)
    if not matches:
        return _not_executed(f"{obj_name.lower()} not found")
    if len(matches) > 1:
        return _ambiguous(obj_name, matches)

    deleted = config.crud.remove(db, matches[0])
    return _executed("deleted", obj_name, deleted)


# ─── find matches (shared by GET / UPDATE / DELETE) ───────────────────────────

def _find_matches(db: Session, config: ObjectConfig, fields: dict, user_id: int) -> list:
    model = config.model
    query = db.query(model).filter(model.user_id == user_id)
    title = _clean_text(fields.get("TITLE"))

    # title: vector search when embedding exists, fallback to ILIKE
    if title:
        try:
            query_vec = embedder.embed(title)
            rows_with_emb = (
                db.query(model)
                .filter(model.user_id == user_id)
                .filter(model.embedding.isnot(None))
                .order_by(model.embedding.op("<=>")(query_vec))
                .limit(10)
                .all()
            )
        except RuntimeError:
            rows_with_emb = []

        # also keep exact ILIKE matches in case some rows have no embedding yet
        ilike_ids = {
            r.id for r in
            query.filter(model.title.ilike(f"%{title}%")).all()
        }
        # merge: vector results first, then any ilike-only hits
        seen = {r.id for r in rows_with_emb}
        candidates = rows_with_emb + [
            r for r in query.filter(model.title.ilike(f"%{title}%")).all()
            if r.id not in seen
        ]
    else:
        candidates = query.order_by(model.created_at.desc()).limit(20).all()

    # apply remaining filters on the candidate set
    return [r for r in candidates if _passes_filters(r, config, fields)]


def _passes_filters(row: Any, config: ObjectConfig, fields: dict) -> bool:
    """Apply STATUS / DATE / TIME / PERSON / LOCATION filters to a single row."""

    # STATUS
    status = _clean_text(fields.get("STATUS"))
    if status and hasattr(row, "status"):
        row_status = row.status.value if hasattr(row.status, "value") else str(row.status)
        if row_status != status:
            return False

    # DATE
    date_val = _parse_date(fields.get("DATE"))
    if date_val:
        if config.date_field and getattr(row, config.date_field, None) != date_val:
            return False

    # TIME
    time_val = _parse_time(fields.get("TIME"))
    if time_val:
        if config.time_field and getattr(row, config.time_field, None) != time_val:
            return False

    # PERSON (Meeting only)
    person = _clean_text(fields.get("PERSON"))
    if person and hasattr(row, "person"):
        row_person = getattr(row, "person") or ""
        if person.lower() not in row_person.lower():
            return False

    # LOCATION (Meeting only)
    location = _clean_text(fields.get("LOCATION"))
    if location and hasattr(row, "location"):
        row_location = getattr(row, "location") or ""
        if location.lower() not in row_location.lower():
            return False

    return True


# ─── embedding helper ─────────────────────────────────────────────────────────

def _update_embedding(db: Session, row: Any) -> None:
    title = getattr(row, "title", None)
    if not title:
        return
    try:
        row.embedding = embedder.embed(title)
        db.commit()
        db.refresh(row)
    except Exception:
        # embedding is best-effort: never fail the main operation
        db.rollback()


# ─── payload builders ─────────────────────────────────────────────────────────

def _payload_for_object(
    config: ObjectConfig,
    obj_name: str,
    fields: dict,
    user_id: int,
    processed: dict,
) -> dict:
    title = _clean_text(fields.get("TITLE"))
    content = _clean_text(fields.get("CONTENT"))

    data: dict[str, Any] = {"user_id": user_id}

    if obj_name == "TASK":
        data.update(
            {
                "title": title,
                "task_date": _parse_date(fields.get("DATE")),
                "task_time": _parse_time(fields.get("TIME")),
                "status": _clean_status(fields.get("STATUS")),
            }
        )
    elif obj_name == "MEETING":
        data.update(
            {
                "title": title or _fallback_title(processed),
                "meeting_date": _parse_date(fields.get("DATE")),
                "meeting_time": _parse_time(fields.get("TIME")),
                "status": _clean_status(fields.get("STATUS")),
                "person": _clean_text(fields.get("PERSON")),
                "location": _clean_text(fields.get("LOCATION")),
            }
        )
    elif obj_name == "NOTE":
        data.update(
            {
                "title": title or _fallback_title(processed),
                "description": content or title or _fallback_title(processed),
            }
        )
    elif obj_name == "PROGRESS":
        data.update(
            {
                "title": title,
                "status": _clean_progress_status(fields.get("STATUS")),
                "field": _clean_text(fields.get("FIELD")),
                "value": _parse_int(fields.get("VALUE")),
            }
        )

    return {key: value for key, value in data.items() if value is not None}


def _update_payload_for_object(config: ObjectConfig, obj_name: str, fields: dict) -> dict:
    data: dict[str, Any] = {}

    if fields.get("TITLE"):
        data["title"] = _clean_text(fields.get("TITLE"))
    if fields.get("STATUS"):
        data["status"] = (
            _clean_progress_status(fields.get("STATUS"))
            if obj_name == "PROGRESS"
            else _clean_status(fields.get("STATUS"))
        )
    if fields.get("DATE") and config.date_field:
        data[config.date_field] = _parse_date(fields.get("DATE"))
    if fields.get("TIME") and config.time_field:
        data[config.time_field] = _parse_time(fields.get("TIME"))
    if obj_name == "MEETING":
        if fields.get("PERSON"):
            data["person"] = _clean_text(fields.get("PERSON"))
        if fields.get("LOCATION"):
            data["location"] = _clean_text(fields.get("LOCATION"))
    if obj_name == "NOTE" and fields.get("CONTENT"):
        data["description"] = _clean_text(fields.get("CONTENT"))
    if obj_name == "PROGRESS":
        if fields.get("FIELD"):
            data["field"] = _clean_text(fields.get("FIELD"))
        if fields.get("VALUE"):
            data["value"] = _parse_int(fields.get("VALUE"))

    return {key: value for key, value in data.items() if value is not None}


# ─── helpers ──────────────────────────────────────────────────────────────────

def _missing_required_for_create(obj_name: str, data: dict) -> list[str]:
    required = {
        "TASK": ["title", "task_date", "task_time", "user_id"],
        "MEETING": ["title", "meeting_date", "meeting_time", "user_id"],
        "NOTE": ["title", "description", "user_id"],
        "PROGRESS": ["title", "user_id"],
    }
    return [field for field in required[obj_name] if data.get(field) is None]


def _serialize(row: Any) -> dict:
    out = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        if isinstance(value, (date, datetime, time)):
            value = value.isoformat()
        out[column.name] = value
    return out


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_status(value: Any) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    normalized = text.lower().replace(" ", "_")
    aliases = {
        "done": "completed",
        "complete": "completed",
        "started": "in_progress",
        "start": "in_progress",
        "todo": "pending",
        "to_do": "pending",
    }
    return aliases.get(normalized, normalized)


def _clean_progress_status(value: Any) -> str | None:
    status = _clean_status(value)
    if status in {"pending", "todo", "to_do"}:
        return "not_started"
    return status


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    text = _clean_text(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _parse_time(value: Any) -> time | None:
    if isinstance(value, time):
        return value
    text = _clean_text(value)
    if not text:
        return None
    try:
        return time.fromisoformat(text)
    except ValueError:
        return None


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _fallback_title(processed: dict) -> str:
    text = _clean_text(processed.get("text")) or _clean_text(processed.get("utterance")) or "Untitled"
    return text[:50]


def _executed(operation: str, obj_name: str, row: Any) -> dict:
    return {
        "status": "EXECUTED",
        "operation": operation,
        "object": obj_name,
        "record": _serialize(row),
    }


def _not_executed(reason: str) -> dict:
    return {
        "status": "NOT_EXECUTED",
        "reason": reason,
    }


def _clarify(reason: str, missing: list[str]) -> dict:
    return {
        "status": "CLARIFY",
        "reason": reason,
        "missing": missing,
    }


def _ambiguous(obj_name: str, matches: list) -> dict:
    return {
        "status": "CLARIFY",
        "reason": f"multiple {obj_name.lower()} records match",
        "matches": [_serialize(row) for row in matches],
    }
