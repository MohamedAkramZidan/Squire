import logging
import re

logger = logging.getLogger(__name__)

MAX_RESPONSE_LENGTH = 1000
FALLBACK_RESPONSE = "I couldn't generate a response from the retrieved notes."

def parse(raw_response: str | None) -> str:
    if raw_response is None:
        logger.info("LLM returned None, using fallback")
        return FALLBACK_RESPONSE

    cleaned = _cleanup(raw_response)

    if not _is_valid(cleaned):
        logger.warning("LLM response failed validation, using fallback")
        return FALLBACK_RESPONSE

    if len(cleaned) > MAX_RESPONSE_LENGTH:
        cleaned = cleaned[:MAX_RESPONSE_LENGTH].rsplit(" ", 1)[0] + "..."
        logger.info("LLM response truncated to %d chars", MAX_RESPONSE_LENGTH)

    return cleaned

def _cleanup(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"^(Answer|Response|Output|Direct Answer)\s*:\s*", "", text, flags=re.IGNORECASE)
    if "Direct Answer:" in text:
        text = text.split("Direct Answer:")[-1]
    elif "Answer:" in text:
        text = text.split("Answer:")[-1]
    elif "Response:" in text:
        text = text.split("Response:")[-1]
        
    # Strip common LLM conversational prefixes
    text = re.sub(r"^(?:Sure|Yes|Of course|Here is|Here's|Here are|Here)[^\n:]*:?\n*", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^(?:Based on the|From the|According to the)[^\n:]*:?\n*", "", text, flags=re.IGNORECASE).strip()

    return text.strip()


def _is_valid(text: str) -> bool:
    if not text:
        return False
    if len(text) < 3:
        return False
    sentences = [s.strip() for s in text.split(".") if s.strip()]
    if len(sentences) >= 3:
        from collections import Counter
        counts = Counter(sentences)
        if counts.most_common(1)[0][1] >= 3:
            return False
    return True
