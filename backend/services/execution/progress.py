import enum
from pydantic import ValidationError
from sqlalchemy.orm import Session

from database.crud.progress import progress as progress_crud
from database.models import Progress, ProgressStatus
from schemas.progress import ProgressCreate, ProgressUpdate

from .helpers import (
    clean_progress_status,
    clean_text,
    clean_title,
    executed,
    not_executed,
    clarify,
    ambiguous,
    find_matches,
    generate_embedding,
    parse_int,
    search_fields_for_update,
    serialize,
)

OBJ_NAME = "PROGRESS"


def execute_progress(db: Session, action: str, fields: dict, user_id: int, processed: dict) -> dict:
    if action == "ADD":
        return _add(db, fields, user_id, processed)
    if action == "GET":
        return _get(db, fields, user_id)
    if action == "UPDATE":
        return _update(db, fields, user_id)
    if action == "DELETE":
        return _delete(db, fields, user_id)
    return not_executed(f"unsupported action: {action}")

def _add(db: Session, fields: dict, user_id: int, processed: dict) -> dict:
    title = clean_title(fields.get("TITLE"), Progress)
    
    status = clean_progress_status(fields.get("STATUS"))
    value = parse_int(fields.get("VALUE"))
    if status is None and value is not None and value != 0:
        status = ProgressStatus.in_progress

    data = {
        "user_id": user_id,
        "title": title,
        "status": status,
        "field": clean_text(fields.get("FIELD")),
        "value": value,
    }
    data = {k: v for k, v in data.items() if v is not None}

    missing = [f for f in ["title", "user_id"] if data.get(f) is None]
    if missing:
        return clarify(f"missing required fields for progress: {missing}", missing)
    
    embedding = generate_embedding(title)

    try:
        payload = ProgressCreate(**data)
    except ValidationError as exc:
        return not_executed(f"invalid create payload: {exc.errors()}")

    created = progress_crud.create(db, payload)

    if embedding is not None:
        created.embedding = embedding
        db.commit()
        db.refresh(created)

    return executed("created", OBJ_NAME, created)


def _get(db: Session, fields: dict, user_id: int) -> dict:
    matches = find_matches(db, Progress, None, None, fields, user_id, action="GET")
    return {
        "status": "EXECUTED",
        "operation": "get",
        "object": OBJ_NAME,
        "count": len(matches),
        "records": [serialize(row) for row in matches],
        "message": f"here your {OBJ_NAME.lower()}",
    }


def _update(db: Session, fields: dict, user_id: int) -> dict:
    search = search_fields_for_update(fields)
    if not search:
        return clarify(f"which progress should I update?", ["TITLE"])

    matches = find_matches(db, Progress, None, None, search, user_id, action="UPDATE")
    if not matches:
        return not_executed("progress not found")
    if len(matches) > 1:
        return ambiguous(OBJ_NAME, matches)

    update_data = _build_update_payload(fields, search)
    if not update_data:
        return clarify("no update fields provided for progress", ["STATUS", "FIELD", "VALUE"])

    if "status" not in update_data:
        new_value = update_data.get("value", matches[0].value)
        if new_value is not None and new_value != 0:
            if matches[0].status == ProgressStatus.not_started:
                update_data["status"] = ProgressStatus.in_progress

    try:
        payload = ProgressUpdate(**update_data)
    except ValidationError as exc:
        return not_executed(f"invalid update payload: {exc.errors()}")

    updated = progress_crud.update(db, matches[0], payload)

    if "title" in update_data:
        embedding = generate_embedding(update_data["title"])
        if embedding is not None:
            updated.embedding = embedding
            db.commit()
            db.refresh(updated)

    return executed("updated", OBJ_NAME, updated, changes=update_data)

def _delete(db: Session, fields: dict, user_id: int) -> dict:
    matches = find_matches(db, Progress, None, None, fields, user_id, action="DELETE")
    if not matches:
        return not_executed("progress not found")
    if len(matches) > 1:
        return ambiguous(OBJ_NAME, matches)

    deleted = progress_crud.remove(db, matches[0])
    return executed("deleted", OBJ_NAME, deleted)

def _build_update_payload(fields: dict, search_fields: dict) -> dict:
    data = {}
    if fields.get("TITLE") and "TITLE" not in search_fields:
        data["title"] = clean_title(fields.get("TITLE"), Progress)
    if fields.get("STATUS"):
        data["status"] = clean_progress_status(fields.get("STATUS"))
    if fields.get("FIELD"):
        data["field"] = clean_text(fields.get("FIELD"))
    if fields.get("VALUE"):
        data["value"] = parse_int(fields.get("VALUE"))
    return {k: v for k, v in data.items() if v is not None}
