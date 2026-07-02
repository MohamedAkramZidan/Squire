import json
import logging
from typing import Any, Optional

from config.settings import settings
from database.redis_client import get_redis

logger = logging.getLogger(__name__)

KEY_PREFIX = "assistant:session"
TTL = settings.redis_session_ttl


def _key(user_id: int) -> str:
    return f"{KEY_PREFIX}:{user_id}"


def get_session(user_id: int) -> Optional[dict]:
    r = get_redis()
    if r is None:
        return None

    try:
        data = r.get(_key(user_id))
        if data is None:
            return None
        return json.loads(data)
    except Exception as exc:
        logger.warning("Failed to read session for user %s: %s", user_id, exc)
        return None


def save_session(user_id: int, session: dict) -> bool:
    r = get_redis()
    if r is None:
        return False

    try:
        r.setex(
            _key(user_id),
            TTL,
            json.dumps(session, default=str),
        )
        logger.info("Session saved for user %s (TTL=%ds)", user_id, TTL)
        return True
    except Exception as exc:
        logger.warning("Failed to save session for user %s: %s", user_id, exc)
        return False


def clear_session(user_id: int) -> bool:
    r = get_redis()
    if r is None:
        return False

    try:
        r.delete(_key(user_id))
        logger.info("Session cleared for user %s", user_id)
        return True
    except Exception as exc:
        logger.warning("Failed to clear session for user %s: %s", user_id, exc)
        return False


def merge_into_session(existing_session: dict, new_processed: dict) -> dict:
    pending = existing_session.get("pending_command", {})
    pending_fields = pending.get("fields", {})

    new_fields = new_processed.get("fields", {})
    for key, value in new_fields.items():
        if value is not None:
            pending_fields[key] = value

    pending["fields"] = pending_fields

    new_action = new_processed.get("action")
    new_object = new_processed.get("object")
    new_action_conf = new_processed.get("action_conf", 0)
    new_object_conf = new_processed.get("object_conf", 0)

    if new_action_conf > 0.95 and new_action != pending.get("action"):
        return None  

    existing_session["pending_command"] = pending
    return existing_session
