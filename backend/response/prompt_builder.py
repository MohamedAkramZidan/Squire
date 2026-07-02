import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

_cache: dict[str, str] = {}

def _load_prompt(name: str) -> str:
    if name in _cache:
        return _cache[name]

    path = PROMPTS_DIR / name
    if not path.exists():
        logger.error("Prompt file not found: %s", path)
        return ""

    text = path.read_text(encoding="utf-8").strip()
    _cache[name] = text
    return text


def build_rag_prompt(question: str, documents: list[str]) -> tuple[str, str]:
    system_prompt = _load_prompt("system.txt")
    user_template = _load_prompt("rag_note.txt")

    formatted_docs = "\n\n".join(
        f"- {doc}" for i, doc in enumerate(documents)
    )

    user_prompt = user_template.format(
        documents=formatted_docs,
        question=question,
    )

    return system_prompt, user_prompt


def build_summarize_prompt(records: list[dict], obj_type: str = "TASK") -> tuple[str, str]:
    system_prompt = _load_prompt("system.txt")

    if obj_type == "PROGRESS":
        user_template = _load_prompt("progress_report.txt")
        formatted = "\n".join(
            f"- {r.get('title', 'untitled')}: {r.get('field', '')} = {r.get('value', '')} ({r.get('status', '')})"
            for r in records
        )
        user_prompt = user_template.format(records=formatted)
    else:
        user_template = _load_prompt("summarize_tasks.txt")
        formatted = "\n".join(
            f"- {r.get('title', 'untitled')} ({r.get('status', 'unknown')}, {r.get('task_date', '')})"
            for r in records
        )
        user_prompt = user_template.format(tasks=formatted)

    return system_prompt, user_prompt
