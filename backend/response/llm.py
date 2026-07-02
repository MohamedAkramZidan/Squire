import logging
from typing import Optional

logger = logging.getLogger(__name__)

_pipeline = None
_model_name: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

def load(model_name: str | None = None) -> None:
    global _pipeline, _model_name

    if model_name:
        _model_name = model_name

    try:
        from transformers import pipeline as hf_pipeline

        _pipeline = hf_pipeline(
            "text-generation",
            model=_model_name,
            device_map="auto",
            torch_dtype="auto",
        )
        logger.info("LLM loaded: %s", _model_name)
    except Exception as exc:
        logger.warning("LLM failed to load (%s): %s — LLM responses will be unavailable.", _model_name, exc)
        _pipeline = None


def is_available() -> bool:
    return _pipeline is not None

def generate(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_new_tokens: int = 1024,
) -> Optional[str]:
    if _pipeline is None:
        logger.warning("LLM not available, cannot generate response")
        return None

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        result = _pipeline(
            messages,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=temperature > 0,
            return_full_text=False,
        )

        if result and len(result) > 0:
            generated = result[0].get("generated_text", "")
            if isinstance(generated, list):
                generated = generated[-1].get("content", "") if generated else ""
            return generated.strip() if generated else None

        return None

    except Exception as exc:
        logger.error("LLM generation failed: %s", exc)
        return None

def get_model_name() -> str:
    return _model_name
