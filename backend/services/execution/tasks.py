from datetime import date, time

from pydantic import ValidationError
from sqlalchemy.orm import Session

from database.crud.tasks import task as task_crud
from database.models import Task, User
from schemas.tasks import TaskCreate, TaskUpdate

from .helpers import (
    clean_status,
    clean_title,
    executed,
    not_executed,
    clarify,
    ambiguous,
    fallback_title,
    find_matches,
    generate_embedding,
    parse_date,
    parse_time,
    search_fields_for_update,
    serialize,
)
from .webhook import trigger_task_webhook

DATE_FIELD = "task_date"
TIME_FIELD = "task_time"
OBJ_NAME = "TASK"


def execute_task(db: Session, action: str, fields: dict, user_id: int, processed: dict) -> dict:
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
    title = clean_title(fields.get("TITLE"), Task)

    data = {
        "user_id": user_id,
        "title": title,
        "task_date": parse_date(fields.get("DATE")) or date.today(),
        "task_time": parse_time(fields.get("TIME")) or time(12, 0),
        "status": clean_status(fields.get("STATUS"), "TASK"),
    }
    data = {k: v for k, v in data.items() if v is not None}

    missing = [f for f in ["title", "user_id"] if data.get(f) is None]
    if missing:
        return clarify(f"missing required fields for task: {missing}", missing)
    embedding = generate_embedding(title)

    try:
        payload = TaskCreate(**data)
    except ValidationError as exc:
        return not_executed(f"invalid create payload: {exc.errors()}")

    created = task_crud.create(db, payload)

    if created.task_date and created.task_time:
        user = db.get(User, user_id)
        email = user.email if user else "moakramzidan@gmail.com"
        trigger_task_webhook(
            task_name=created.title, 
            deadline_date=created.task_date.isoformat(), 
            deadline_time=created.task_time.isoformat(), 
            email=email
        )

    if embedding is not None:
        created.embedding = embedding
        db.commit()
        db.refresh(created)

    return executed("created", OBJ_NAME, created)


def _get(db: Session, fields: dict, user_id: int) -> dict:
    matches = find_matches(db, Task, DATE_FIELD, TIME_FIELD, fields, user_id, action="GET")
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
        return clarify(f"which task should I update?", ["TITLE"])

    matches = find_matches(db, Task, DATE_FIELD, TIME_FIELD, search, user_id, action="UPDATE")
    if not matches:
        return not_executed("task not found")
    if len(matches) > 1:
        return ambiguous(OBJ_NAME, matches)

    update_data = _build_update_payload(fields, search)
    if not update_data:
        return clarify("no update fields provided for task", ["STATUS", "DATE", "TIME"])

    try:
        payload = TaskUpdate(**update_data)
    except ValidationError as exc:
        return not_executed(f"invalid update payload: {exc.errors()}")

    updated = task_crud.update(db, matches[0], payload)

    if "title" in update_data:
        embedding = generate_embedding(update_data["title"])
        if embedding is not None:
            updated.embedding = embedding
            db.commit()
            db.refresh(updated)

    return executed("updated", OBJ_NAME, updated, changes=update_data)


def _delete(db: Session, fields: dict, user_id: int) -> dict:
    matches = find_matches(db, Task, DATE_FIELD, TIME_FIELD, fields, user_id, action="DELETE")
    if not matches:
        return not_executed("task not found")
    if len(matches) > 1:
        return ambiguous(OBJ_NAME, matches)

    deleted = task_crud.remove(db, matches[0])
    return executed("deleted", OBJ_NAME, deleted)

def _build_update_payload(fields: dict, search_fields: dict) -> dict:
    data = {}
    if fields.get("TITLE") and "TITLE" not in search_fields:
        data["title"] = clean_title(fields.get("TITLE"), Task)
    if fields.get("STATUS"):
        data["status"] = clean_status(fields.get("STATUS"), "TASK")
    if fields.get("DATE"):
        data["task_date"] = parse_date(fields.get("DATE"))
    if fields.get("TIME"):
        data["task_time"] = parse_time(fields.get("TIME"))
    return {k: v for k, v in data.items() if v is not None}
