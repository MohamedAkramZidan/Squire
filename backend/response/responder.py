import logging

from response import templates
from response import prompt_builder
from response import llm
from response import parser

logger = logging.getLogger(__name__)

def generate_response(
    decision: dict,
    execution: dict | None = None,
    original_text: str | None = None,
) -> str:
    decision_type = decision.get("decision", "")

    if decision_type in ("CLARIFY", "RETRY_NER", "REJECT"):
        return templates.render_decision(decision)
    
    if decision_type == "EXECUTE" and execution is not None:
        return _handle_execution_response(execution, original_text)

    return templates.render_decision(decision)

def _handle_execution_response(
    execution: dict,
    original_text: str | None = None,
) -> str:
    status = execution.get("status", "")
    operation = execution.get("operation", "")
    obj = execution.get("object", "")

    if status in ("CLARIFY", "NOT_EXECUTED"):
        return templates.render_execution(execution)

    if _needs_llm(operation, obj, execution, original_text):
        llm_response = _generate_llm_response(execution, original_text)
        if llm_response is not None:
            return llm_response
        logger.info("LLM unavailable or failed, falling back to template")

    return templates.render_execution(execution, obj)

def _needs_llm(operation: str, obj: str, execution: dict, original_text: str | None) -> bool:
    if operation != "get":
        return False

    records = execution.get("records", [])
    if not records:
        return False

    if obj == "NOTE" and original_text:
        return True
    
    if obj == "TASK" and len(records) >= 3:
        return True
    
    if obj == "PROGRESS" and records:
        return True

    return False


def _generate_llm_response(execution: dict, original_text: str | None) -> str | None:
    if not llm.is_available():
        return None

    records = execution.get("records", [])
    if not records:
        return None

    obj = execution.get("object", "")

    if obj == "NOTE" and original_text:
        documents = []
        for record in records:
            title = record.get("title", "")
            description = record.get("description", "")
            documents.append(f"Title: {title}\n{description}")
        system_prompt, user_prompt = prompt_builder.build_rag_prompt(
            question=original_text,
            documents=documents,
        )
    elif obj == "TASK":
        system_prompt, user_prompt = prompt_builder.build_summarize_prompt(records, "TASK")
    elif obj == "PROGRESS":
        system_prompt, user_prompt = prompt_builder.build_summarize_prompt(records, "PROGRESS")
    else:
        return None

    raw = llm.generate(system_prompt, user_prompt)

    return parser.parse(raw)
