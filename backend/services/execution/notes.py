from pydantic import ValidationError
from sqlalchemy.orm import Session

from database.crud.notes import note as note_crud
from database.models import Note
from schemas.notes import NoteCreate, NoteUpdate

from .helpers import (
    clean_text,
    clean_title,
    executed,
    not_executed,
    clarify,
    ambiguous,
    fallback_title,
    find_matches,
    generate_embedding,
    search_fields_for_update,
    serialize,
)

OBJ_NAME = "NOTE"

def execute_note(db: Session, action: str, fields: dict, user_id: int, processed: dict) -> dict:
    if action == "ADD":
        return _add(db, fields, user_id, processed)
    if action == "GET":
        return _get(db, fields, user_id, processed)
    if action == "UPDATE":
        return _update(db, fields, user_id, processed)
    if action == "DELETE":
        return _delete(db, fields, user_id, processed)
    return not_executed(f"unsupported action: {action}")

def _add(db: Session, fields: dict, user_id: int, processed: dict) -> dict:
    full_text = processed.get("text") or processed.get("utterance") or ""
    title = clean_title(fields.get("TITLE"), Note) or _note_title_from_text(full_text) or fallback_title(processed)
    content = fields.get("CONTENT")
    description = full_text or clean_text(content) or title or fallback_title(processed)

    data = {
        "user_id": user_id,
        "title": title,
        "description": description,
    }

    missing = [f for f in ["title", "description", "user_id"] if data.get(f) is None]
    if missing:
        return clarify(f"missing required fields for note: {missing}", missing)

    embedding = generate_embedding(description or title)

    try:
        payload = NoteCreate(**data)
    except ValidationError as exc:
        return not_executed(f"invalid create payload: {exc.errors()}")

    created = note_crud.create(db, payload)

    if embedding is not None:
        created.embedding = embedding
        db.commit()
        db.refresh(created)

    return executed("created", OBJ_NAME, created)

def _get(db: Session, fields: dict, user_id: int, processed: dict) -> dict:
    matches = find_matches(db, Note, None, None, fields, user_id, action="GET", processed=processed)
    return {
        "status": "EXECUTED",
        "operation": "get",
        "object": OBJ_NAME,
        "count": len(matches),
        "records": [serialize(row) for row in matches],
        "message": f"here your {OBJ_NAME.lower()}",
    }

def _update(db: Session, fields: dict, user_id: int, processed: dict) -> dict:
    search = search_fields_for_update(fields)
    if not search and not processed.get("text") and "TARGET_ID" not in fields:
        return clarify("which note should I update?", ["TITLE"])
    matches = find_matches(db, Note, None, None, search, user_id, action="UPDATE", processed=processed)
    if not matches:
        return not_executed("note not found")
    if len(matches) > 1:
        return ambiguous(OBJ_NAME, matches)

    update_data = _build_update_payload(fields, search)

    if processed and processed.get("text"):
        update_data["description"] = processed.get("text")

    if not update_data:
        return clarify("no update fields provided for note", ["CONTENT"])

    try:
        payload = NoteUpdate(**update_data)
    except ValidationError as exc:
        return not_executed(f"invalid update payload: {exc.errors()}")

    updated = note_crud.update(db, matches[0], payload)

    if "title" in update_data or "description" in update_data:
        embed_text = clean_text(getattr(updated, "description", None)) or clean_text(getattr(updated, "title", None))
        embedding = generate_embedding(embed_text)
        if embedding is not None:
            updated.embedding = embedding
            db.commit()
            db.refresh(updated)

    return executed("updated", OBJ_NAME, updated, changes=update_data)


def _delete(db: Session, fields: dict, user_id: int, processed: dict) -> dict:
    matches = find_matches(db, Note, None, None, fields, user_id, action="DELETE", processed=processed)
    if not matches:
        return not_executed("note not found")
    if len(matches) > 1:
        return ambiguous(OBJ_NAME, matches)

    deleted = note_crud.remove(db, matches[0])
    return executed("deleted", OBJ_NAME, deleted)

def _note_title_from_text(text: str | None) -> str | None:
    clean = clean_text(text)
    if not clean:
        return None

    for prefix in ("add note", "note", "remember", "save note"):
        if clean.lower().startswith(prefix):
            clean = clean[len(prefix):].strip(" :-")
            break

    return clean[:50] or None


def _build_update_payload(fields: dict, search_fields: dict) -> dict:
    data = {}
    if fields.get("TITLE") and "TITLE" not in search_fields:
        data["title"] = clean_title(fields.get("TITLE"), Note)
    if fields.get("CONTENT"):
        data["description"] = clean_text(fields.get("CONTENT"))
    return {k: v for k, v in data.items() if v is not None}
