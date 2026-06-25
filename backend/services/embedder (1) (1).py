from __future__ import annotations

import logging
from typing import List, Sequence

logger = logging.getLogger(__name__)

_model = None
MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


def load():
    global _model
    from sentence_transformers import SentenceTransformer
    _model = SentenceTransformer(MODEL_NAME)
    logger.info("Embedding model '%s' loaded (dim=%d).", MODEL_NAME, EMBEDDING_DIM)


def embed(text: str) -> List[float]:
    if _model is None:
        load()
    return _model.encode(text, normalize_embeddings=True, convert_to_numpy=True).astype(float).tolist()


def embed_batch(texts: Sequence[str], batch_size: int = 32) -> List[List[float]]:
    if _model is None:
        load()
    return _model.encode(
        list(texts), batch_size=batch_size,
        normalize_embeddings=True, convert_to_numpy=True,
    ).astype(float).tolist()


def get_embedding_dimension() -> int:
    return EMBEDDING_DIM


def get_model_name() -> str:
    return MODEL_NAME
