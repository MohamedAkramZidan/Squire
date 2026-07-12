from datetime import time

from pydantic import ValidationError
from sqlalchemy.orm import Session

from database.crud.meetings import meeting as meeting_crud
from database.models import Meeting, User
from schemas.meetings import MeetingCreate, MeetingUpdate

from .helpers import (
    clean_status,
    clean_text,
    clean_title,
    executed,
    not_executed,
    clarify,
    ambiguous,

    find_matches,
    generate_embedding,
    parse_date,
    parse_time,
    search_fields_for_update,
    serialize,
)
from .webhook import trigger_meeting_webhook

DATE_FIELD = "meeting_date"
TIME_FIELD = "meeting_time"
OBJ_NAME = "MEETING"


def execute_meeting(db: Session, action: str, fields: dict, user_id: int, processed: dict) -> dict:
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
    title = clean_title(fields.get("TITLE"), Meeting) or "Meeting"

    data = {
        "user_id": user_id,
        "title": title,
        "meeting_date": parse_date(fields.get("DATE")) or date.today(),
        "meeting_time": parse_time(fields.get("TIME")) or time(12, 0),
        "status": clean_status(fields.get("STATUS"), "MEETING"),
        "person": clean_text(fields.get("PERSON")),
        "location": clean_text(fields.get("LOCATION")),
    }
    data = {k: v for k, v in data.items() if v is not None}

    missing = [f for f in ["title", "meeting_date", "user_id"] if data.get(f) is None]
    if missing:
        return clarify(f"missing required fields for meeting: {missing}", missing)

    embedding = generate_embedding(title)

    try:
        payload = MeetingCreate(**data)
    except ValidationError as exc:
        return not_executed(f"invalid create payload: {exc.errors()}")

    created = meeting_crud.create(db, payload)

    if created.meeting_date and created.meeting_time:
        user = db.get(User, user_id)
        email = user.email if user else "moakramzidan@gmail.com"
        
        desc_parts = []
        if created.person:
            desc_parts.append(f"Person: {created.person}")
        if created.location:
            desc_parts.append(f"Location: {created.location}")
        description = " | ".join(desc_parts)

        trigger_meeting_webhook(
            topic=created.title,
            deadline_date=created.meeting_date.isoformat(),
            deadline_time=created.meeting_time.isoformat(),
            email=email,
            description=description
        )

    if embedding is not None:
        created.embedding = embedding
        db.commit()
        db.refresh(created)

    return executed("created", OBJ_NAME, created)


def _get(db: Session, fields: dict, user_id: int) -> dict:
    matches = find_matches(db, Meeting, DATE_FIELD, TIME_FIELD, fields, user_id, action="GET")
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
        return clarify(f"which meeting should I update?", ["TITLE"])

    matches = find_matches(db, Meeting, DATE_FIELD, TIME_FIELD, search, user_id, action="UPDATE")
    if not matches:
        return not_executed("meeting not found")
    if len(matches) > 1:
        return ambiguous(OBJ_NAME, matches)

    update_data = _build_update_payload(fields, search)
    if not update_data:
        return clarify("no update fields provided for meeting", ["STATUS", "DATE", "TIME"])

    try:
        payload = MeetingUpdate(**update_data)
    except ValidationError as exc:
        return not_executed(f"invalid update payload: {exc.errors()}")

    updated = meeting_crud.update(db, matches[0], payload)

    if "title" in update_data:
        embedding = generate_embedding(update_data["title"])
        if embedding is not None:
            updated.embedding = embedding
            db.commit()
            db.refresh(updated)

    return executed("updated", OBJ_NAME, updated, changes=update_data)


def _delete(db: Session, fields: dict, user_id: int) -> dict:
    matches = find_matches(db, Meeting, DATE_FIELD, TIME_FIELD, fields, user_id, action="DELETE")
    if not matches:
        return not_executed("meeting not found")
    if len(matches) > 1:
        return ambiguous(OBJ_NAME, matches)

    deleted = meeting_crud.remove(db, matches[0])
    return executed("deleted", OBJ_NAME, deleted)

def _build_update_payload(fields: dict, search_fields: dict) -> dict:
    data = {}
    if fields.get("TITLE") and "TITLE" not in search_fields:
        data["title"] = clean_title(fields.get("TITLE"), Meeting)
    if fields.get("STATUS"):
        data["status"] = clean_status(fields.get("STATUS"), "MEETING")
    if fields.get("DATE"):
        data["meeting_date"] = parse_date(fields.get("DATE"))
    if fields.get("TIME"):
        data["meeting_time"] = parse_time(fields.get("TIME"))
    if fields.get("PERSON") and "PERSON" not in search_fields:
        data["person"] = clean_text(fields.get("PERSON"))
    if fields.get("LOCATION") and "LOCATION" not in search_fields:
        data["location"] = clean_text(fields.get("LOCATION"))
    return {k: v for k, v in data.items() if v is not None}
