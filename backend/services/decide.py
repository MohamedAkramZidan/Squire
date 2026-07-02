"""
Decision Engine — the system controller.

Architecture spec:
  - It decides what happens next
  - It does NOT execute CRUD operations
  - It only routes requests
  - It checks Redis FIRST for active sessions
  - If session exists: merge entities, revalidate, continue
  - If no session: process as new command

Possible decisions: EXECUTE, CLARIFY, RETRY, REJECT
"""

import logging

from services import state_manager

logger = logging.getLogger(__name__)

INTENT_MIN = 0.80
ENTITY_MIN = 0.85

CLARIFY_QUESTIONS = {
    "DATE": "What date?",
    "TIME": "What time?",
    "PERSON": "Who should I include?",
    "TITLE": "What should I call it?",
    "LOCATION": "Where?",
    "STATUS": "What status?",
    "FIELD": "Which field?",
    "VALUE": "What value?",
    "TARGET_SELECTION": "Which one do you mean?",
}


def decide(processed: dict, user_id: int | None = None) -> dict:
    """
    Main entry point. Checks Redis for an active session first,
    then evaluates the (possibly merged) command.
    """
    # ── Step 1: Check Redis for active session ────────────────────────────
    if user_id is not None:
        session = state_manager.get_session(user_id)
        if session is not None:
            return _handle_active_session(session, processed, user_id)

    # ── Step 2: No active session — evaluate as a new command ─────────────
    return _evaluate_new_command(processed, user_id)


def _handle_active_session(session: dict, processed: dict, user_id: int) -> dict:
    """
    An active workflow exists in Redis. The user is replying to a CLARIFY question.

    CRITICAL: We SKIP all NLU confidence checks (action, object, entity).
    The user's reply is ALWAYS treated as the answer to the specific
    question we asked — never as a new command to reject.

    Flow:
      1. TARGET_SELECTION → short-circuit with the selected ID
      2. Any other entity → extract from raw text, merge, execute
    """
    waiting_for = session.get("waiting_for")
    text = processed.get("text", "").strip()
    pending = session.get("pending_command", {})

    logger.info(
        "Active session for user %s: waiting_for=%s, reply='%s'",
        user_id, waiting_for, text,
    )

    # ── TARGET_SELECTION: short-circuit completely ────────────────────────
    if waiting_for == "TARGET_SELECTION":
        try:
            idx = int(text) - 1
            matches = session.get("matches", [])
            if 0 <= idx < len(matches):
                pending_fields = pending.get("fields", {})
                pending_fields["TARGET_ID"] = matches[idx]["id"]
                state_manager.clear_session(user_id)
                logger.info("Target selected: index %d, id %s", idx, matches[idx]["id"])
                return _decision("EXECUTE", "target selected from ambiguous list", {
                    **processed,
                    "action": pending.get("action"),
                    "object": pending.get("object"),
                    "fields": pending_fields,
                    "ok": True,
                    "missing": [],
                })
        except ValueError:
            pass
        state_manager.clear_session(user_id)
        return _decision("REJECT", "invalid selection — please start over", processed)

    # ── Entity extraction: pull the answer from raw text ──────────────────
    # The NLU may have extracted some fields; start with those.
    # CRITICAL UPDATE: Strict Targeting. We only care about the field we asked for.
    extracted_fields = {}
    
    if waiting_for == "ACTION":
        # If the NLU found an action in the clarification, take it
        new_action = processed.get("action")
        if new_action:
            pending["action"] = new_action
        else:
            # Maybe they just typed "update". Need manual mapping if NLU fails.
            pass
    elif waiting_for == "OBJECT":
        # If the NLU found an object in the clarification, take it
        new_obj = processed.get("object")
        if new_obj:
            pending["object"] = new_obj
        else:
            pass
    else:
        # We are waiting for an entity. Take ONLY that entity from the NLU.
        if waiting_for in processed.get("fields", {}):
            extracted_fields[waiting_for] = processed["fields"][waiting_for]
            logger.info("NLU strict extraction: %s = '%s'", waiting_for, extracted_fields[waiting_for])

        # If the NLU didn't extract the entity we're waiting for,
        # parse the raw text directly using the appropriate parser.
        if waiting_for not in extracted_fields and text:
            parsed_value = _parse_entity_from_text(waiting_for, text)
            if parsed_value is not None:
                extracted_fields[waiting_for] = parsed_value
                logger.info("Fallback extraction: %s = '%s'", waiting_for, parsed_value)

        # ── Merge into pending command ────────────────────────────────────────
        pending_fields = pending.get("fields", {})
        for key, value in extracted_fields.items():
            if value is not None:
                pending_fields[key] = value

    # ── Revalidate required fields ────────────────────────────────────────
    from postprocess.config import REQUIRED
    action = pending.get("action")
    obj = pending.get("object")

    required = REQUIRED.get((action, obj), [])
    pending_fields = pending.get("fields", {})
    missing = [f for f in required if f not in pending_fields]

    if not action or not obj or missing:
        # We are still missing core components (or the user gave an invalid answer).
        state_manager.clear_session(user_id)
        logger.info("Core components still missing after reply: action=%s, obj=%s, missing=%s", action, obj, missing)
        return _decision(
            "REJECT",
            f"Could not complete command after clarification.",
            processed,
        )

    # ── All fields present — clear session and execute ────────────────────
    state_manager.clear_session(user_id)
    logger.info("Session completed for user %s, proceeding to EXECUTE", user_id)

    return _decision("EXECUTE", "pending command completed with merged entities", {
        **processed,
        "action": action,
        "object": obj,
        "fields": pending_fields,
        "ok": True,
        "missing": [],
    })


def _parse_entity_from_text(entity_type: str, text: str):
    """
    Extract a specific entity value directly from the user's raw text.
    Used as a fallback when NLU fails to extract the entity we asked for.
    Returns None if parsing fails.
    """
    from postprocess.date_parser import resolve_date
    from postprocess.time_parser import resolve_time
    from datetime import datetime

    text = text.strip()
    if not text:
        return None

    if entity_type == "DATE":
        return resolve_date(text, datetime.now())
    elif entity_type == "TIME":
        return resolve_time(text)
    elif entity_type in ("TITLE", "PERSON", "LOCATION", "FIELD"):
        # For free-text entities, the entire reply IS the value
        return text
    elif entity_type == "STATUS":
        # Normalize common status aliases
        aliases = {
            "done": "completed", "complete": "completed", "completed": "completed",
            "started": "in_progress", "in progress": "in_progress",
            "todo": "pending", "to do": "pending", "pending": "pending",
            "not started": "not_started", "cancelled": "cancelled",
        }
        return aliases.get(text.lower(), text.lower())
    elif entity_type == "VALUE":
        try:
            return int(text)
        except ValueError:
            return text
    return None


def _evaluate_new_command(processed: dict, user_id: int | None) -> dict:
    """
    Evaluate a fresh command (no active Redis session).
    """
    action_conf = processed.get("action_conf", 0)
    object_conf = processed.get("object_conf", 0)
    ok = processed.get("ok", False)
    missing = processed.get("missing", [])
    entities = processed.get("entities", [])

    # ── Confidence check ──────────────────────────────────────────────────
    # If action or object confidence is low, trigger CLARIFY instead of REJECT.
    if action_conf < INTENT_MIN:
        if user_id is not None:
            state_manager.save_session(user_id, {
                "status": "waiting_for_entity",
                "pending_command": {
                    "action": None, # Will be filled by reply
                    "object": processed.get("object"),
                    "fields": processed.get("fields", {}),
                },
                "waiting_for": "ACTION",
            })
        return _decision(
            "CLARIFY",
            f"action confidence too low ({action_conf:.2f})",
            processed,
            questions=["What do you want to do?"]
        )

    if object_conf < INTENT_MIN:
        if user_id is not None:
            state_manager.save_session(user_id, {
                "status": "waiting_for_entity",
                "pending_command": {
                    "action": processed.get("action"),
                    "object": None, # Will be filled by reply
                    "fields": processed.get("fields", {}),
                },
                "waiting_for": "OBJECT",
            })
        return _decision(
            "CLARIFY",
            f"object confidence too low ({object_conf:.2f})",
            processed,
            questions=["Which object are you referring to? (e.g. note, task, meeting)"]
        )

    # ── Intermediate entity confidence → CLARIFY ──────────────────────────
    # Entities < 0.50 are dropped in processor.py.
    # Entities >= 0.50 and < 0.85 (ENTITY_MIN) trigger CLARIFY.
    # CRITICAL: For NOTES, we completely bypass entity clarification because they rely on full-text search.
    intermediate_entities = []
    if processed.get("object") != "NOTE":
        intermediate_entities = [
            e["type"] for e in entities
            if 0.50 <= e.get("confidence", 1) < ENTITY_MIN
        ]
    if intermediate_entities:
        clarify_entity = intermediate_entities[0]
        if user_id is not None:
            state_manager.save_session(user_id, {
                "status": "waiting_for_entity",
                "pending_command": {
                    "action": processed.get("action"),
                    "object": processed.get("object"),
                    "fields": processed.get("fields", {}),
                },
                "waiting_for": clarify_entity,
            })
        question = CLARIFY_QUESTIONS.get(clarify_entity, f"Can you clarify the {clarify_entity.lower()}?")
        return _decision(
            "CLARIFY",
            f"intermediate confidence on entity: {clarify_entity}",
            processed,
            questions=[question]
        )

    # ── Missing required entities → CLARIFY ───────────────────────────────
    if not ok and missing:
        # Store pending command in Redis for multi-turn completion
        if user_id is not None:
            session = {
                "status": "waiting_for_entity",
                "pending_command": {
                    "action": processed.get("action"),
                    "object": processed.get("object"),
                    "fields": processed.get("fields", {}),
                },
                "waiting_for": missing[0],
            }
            state_manager.save_session(user_id, session)

        questions = [
            CLARIFY_QUESTIONS.get(m, f"Can you provide {m.lower()}?")
            for m in missing
        ]
        return _decision(
            "CLARIFY",
            f"missing required entities: {missing}",
            processed,
            questions=questions,
        )

    # ── All good → EXECUTE ────────────────────────────────────────────────
    return _decision("EXECUTE", "intent clear, all entities present", processed)


def _decision(decision: str, reason: str, data: dict, questions: list = None) -> dict:
    out = {
        "decision": decision,
        "reason": reason,
        "data": data,
    }
    if questions:
        out["questions"] = questions
    return out
