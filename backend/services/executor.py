from sqlalchemy.orm import Session

from database.models import User
from services.execution import execute_task, execute_meeting, execute_note, execute_progress


_DISPATCHERS = {
    "TASK": execute_task,
    "MEETING": execute_meeting,
    "NOTE": execute_note,
    "PROGRESS": execute_progress,
}


def execute_intent(db: Session, processed: dict, user_id: int | None) -> dict:
    try:
        if user_id is None:
            return _not_executed("missing user_id")

        if not db.get(User, user_id):
            return _not_executed("user not found")

        action = processed.get("action")
        obj_name = processed.get("object")
        fields = processed.get("fields", {})

        dispatcher = _DISPATCHERS.get(obj_name)
        if not dispatcher:
            return _not_executed(f"unsupported object: {obj_name}")

        return dispatcher(db, action, fields, user_id, processed)

    except Exception as exc:
        db.rollback()
        return _not_executed(f"execution failed: {type(exc).__name__}: {exc}")


def _not_executed(reason: str) -> dict:
    return {
        "status": "NOT_EXECUTED",
        "reason": reason,
    }
