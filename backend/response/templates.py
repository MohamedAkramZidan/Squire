_CREATED = {
    "TASK": 'Task "{title}" has been created successfully.',
    "MEETING": 'Meeting "{title}" has been scheduled successfully.',
    "NOTE": 'Note "{title}" has been saved successfully.',
    "PROGRESS": 'Progress "{title}" has been recorded successfully.',
}

_UPDATED = {
    "TASK": 'Task "{title}" has been updated successfully.',
    "MEETING": 'Meeting "{title}" has been updated successfully.',
    "NOTE": 'Note "{title}" has been updated successfully.',
    "PROGRESS": 'Progress "{title}" has been updated successfully.',
}

_DELETED = {
    "TASK": 'Task "{title}" has been deleted.',
    "MEETING": 'Meeting "{title}" has been deleted.',
    "NOTE": 'Note "{title}" has been deleted.',
    "PROGRESS": 'Progress "{title}" has been deleted.',
}

_GET_SINGLE = {
    "TASK": "Here is your task:",
    "MEETING": "Here is your meeting:",
    "NOTE": "Here is your note:",
    "PROGRESS": "Here is your progress record:",
}

_GET_MULTIPLE = {
    "TASK": "Here are your tasks:",
    "MEETING": "Here are your meetings:",
    "NOTE": "Here are your notes:",
    "PROGRESS": "Here are your progress records:",
}

_GET_NONE = {
    "TASK": "No tasks found matching your request.",
    "MEETING": "No meetings found matching your request.",
    "NOTE": "No notes found matching your request.",
    "PROGRESS": "No progress records found matching your request.",
}

_REJECT_TEMPLATE = "I'm not confident enough in what you're asking. Could you rephrase your request?"

_RETRY_TEMPLATE = "I'm having trouble understanding some details. Could you rephrase your request?"

_NOT_EXECUTED_TEMPLATE = "I couldn't complete that action. {reason}"

def render_execution(execution: dict, obj_name: str | None = None) -> str:
    status = execution.get("status", "")
    operation = execution.get("operation", "")
    obj = obj_name or execution.get("object", "")
    record = execution.get("record", {})
    title = record.get("title", "untitled")

    if status == "EXECUTED":
        if operation == "created":
            return _CREATED.get(obj, f'{obj} "{title}" created.').format(title=title)
        elif operation == "updated":
            changes = execution.get("changes", {})
            base = _UPDATED.get(obj, f'{obj} "{title}" updated.').format(title=title)
            if changes:
                details = ", ".join(f"{k} → {v}" for k, v in changes.items())
                return f"{base} Changes: {details}."
            return base
        elif operation == "deleted":
            return _DELETED.get(obj, f'{obj} "{title}" deleted.').format(title=title)
        elif operation == "get":
            count = execution.get("count", 0)
            records = execution.get("records", [])
            if count == 0:
                return _GET_NONE.get(obj, "No records found.")
            elif count == 1:
                header = _GET_SINGLE.get(obj, "Here is your record:")
                return f"{header}\n{_format_record(records[0], obj)}"
            else:
                header = _GET_MULTIPLE.get(obj, "Here are your records:")
                items = "\n".join(
                    f"  {i+1}. {_format_record_short(r, obj)}"
                    for i, r in enumerate(records)
                )
                return f"{header}\n{items}"

    if status == "NOT_EXECUTED":
        reason = execution.get("reason", "unknown error")
        return _NOT_EXECUTED_TEMPLATE.format(reason=reason)

    if status == "CLARIFY":
        return render_clarify_from_execution(execution)

    return "Something unexpected happened."


def render_decision(decision: dict) -> str:
    decision_type = decision.get("decision", "")

    if decision_type == "CLARIFY":
        questions = decision.get("questions", [])
        if questions:
            return "\n".join(questions)
        missing = decision.get("data", {}).get("missing", [])
        if missing:
            return f"I need a bit more information: {', '.join(missing)}."
        return "Could you provide more details?"

    if decision_type == "RETRY_NER":
        return _RETRY_TEMPLATE

    if decision_type == "REJECT":
        return _REJECT_TEMPLATE

    return ""


def render_clarify_from_execution(execution: dict) -> str:
    matches = execution.get("matches")
    if matches:
        obj = execution.get("object", "record").lower()
        header = f"I found multiple matching {obj}s:"
        items = "\n".join(
            f"  {i+1}. {_format_record_short(m, execution.get('object', ''))}"
            for i, m in enumerate(matches)
        )
        return f"{header}\n{items}\nReply with the number of the one you mean."

    reason = execution.get("reason", "")
    missing = execution.get("missing", [])
    if missing:
        from services.decide import CLARIFY_QUESTIONS
        questions = [
            CLARIFY_QUESTIONS.get(m, f"Can you provide {m.lower()}?")
            for m in missing
        ]
        return "\n".join(questions)

    return f"I need more information: {reason}"

def _format_record(record: dict, obj: str) -> str:
    title = record.get("title", "untitled")
    lines = [f"  📌 {title}"]

    if obj == "TASK":
        if record.get("task_date"):
            lines.append(f"  📅 Date: {record['task_date']}")
        if record.get("task_time"):
            lines.append(f"  🕐 Time: {record['task_time']}")
        if record.get("status"):
            lines.append(f"  📊 Status: {record['status']}")

    elif obj == "MEETING":
        if record.get("meeting_date"):
            lines.append(f"  📅 Date: {record['meeting_date']}")
        if record.get("meeting_time"):
            lines.append(f"  🕐 Time: {record['meeting_time']}")
        if record.get("person"):
            lines.append(f"  👤 With: {record['person']}")
        if record.get("location"):
            lines.append(f"  📍 Location: {record['location']}")
        if record.get("status"):
            lines.append(f"  📊 Status: {record['status']}")

    elif obj == "NOTE":
        desc = record.get("description", "")
        if desc:
            preview = desc[:120] + "..." if len(desc) > 120 else desc
            lines.append(f"  📝 {preview}")

    elif obj == "PROGRESS":
        if record.get("field"):
            lines.append(f"  📊 Field: {record['field']}")
        if record.get("value") is not None:
            lines.append(f"  🔢 Value: {record['value']}")
        if record.get("status"):
            lines.append(f"  📊 Status: {record['status']}")

    return "\n".join(lines)


def _format_record_short(record: dict, obj: str) -> str:
    title = record.get("title", "untitled")
    parts = [title]

    if obj == "TASK" and record.get("task_date"):
        parts.append(f"({record['task_date']})")
    elif obj == "MEETING":
        if record.get("meeting_date"):
            parts.append(f"({record['meeting_date']})")
        if record.get("person"):
            parts.append(f"with {record['person']}")
    elif obj == "NOTE":
        desc = record.get("description", "")
        if desc:
            parts.append(f"— {desc[:60]}...")
    elif obj == "PROGRESS" and record.get("field"):
        parts.append(f"[{record['field']}]")

    return " ".join(parts)
