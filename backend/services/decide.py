INTENT_MIN    = 0.80
ENTITY_MIN    = 0.80

CLARIFY_QUESTIONS = {
    "DATE":     "What date?",
    "TIME":     "What time?",
    "PERSON":   "Who should I include?",
    "TITLE":    "What should I call it?",
    "LOCATION": "Where?",
    "STATUS":   "What status?",
    "FIELD":    "Which field?",
    "VALUE":    "What value?",
}

def decide(processed: dict) -> dict:
    action_conf  = processed.get("action_conf", 0)
    object_conf  = processed.get("object_conf", 0)
    ok           = processed.get("ok", False)
    missing      = processed.get("missing", [])
    entities     = processed.get("entities", [])

    if action_conf < INTENT_MIN or object_conf < INTENT_MIN:
        return _decision(
            "REJECT",
            f"intent confidence too low "
            f"(action={action_conf:.2f}, object={object_conf:.2f})",
            processed,
        )

    if not ok and missing:
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

    low_conf = [
        e["type"] for e in entities
        if e.get("confidence", 1) < ENTITY_MIN
    ]
    if low_conf:
        return _decision(
            "RETRY_NER",
            f"low confidence on entities: {low_conf}",
            processed,
        )

    return _decision("EXECUTE", "intent clear, all entities present", processed)

def _decision(decision: str, reason: str, data: dict, questions: list = None) -> dict:
    out = {
        "decision": decision,
        "reason":   reason,
        "data":     data,
    }
    if questions:
        out["questions"] = questions
    return out
