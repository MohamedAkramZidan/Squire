from __future__ import annotations

import os
from typing import Dict, List, Tuple

import numpy as np

from services.embedder import embed_batch, embed

STATUS_MAPPING_THRESHOLD = float(
    os.getenv("STATUS_MAPPING_THRESHOLD", "0.80")
)

STATUS_ALIASES: Dict[str, Dict[str, List[str]]] = {
    "TASK": {
        "completed": [
            "completed",
            "done",
            "finished",
            "complete",
            "finish report",
        ],
        "in_progress": [
            "working",
            "working on it",
            "doing",
            "in progress",
        ],
        "pending": [
            "pending",
            "waiting",
        ],
    },

    "MEETING": {
        "scheduled": [
            "scheduled",
            "booked",
            "reserved",
        ],
        "completed": [
            "completed",
            "done",
            "finished",
        ],
        "in_progress": [
            "working",
            "working on it",
            "doing",
            "in progress",
        ]
    },

    "PROGRESS": {
        "not_started": [
            "not started",
            "not started yet",
            "haven't started",
        ],
        "in_progress": [
            "working",
            "working on it",
            "doing",
        ],
        "completed": [
            "done",
            "finished",
            "completed",
        ],
    },
}

_embedding_cache = {}


def _build_cache():
    """
    Build embeddings once at startup.
    """
    global _embedding_cache

    if _embedding_cache:
        return

    for object_type, statuses in STATUS_ALIASES.items():

        _embedding_cache[object_type] = {}

        for canonical_status, aliases in statuses.items():

            vectors = embed_batch(aliases)

            _embedding_cache[object_type][canonical_status] = list(
                zip(aliases, vectors)
            )


def map_status(
    raw_status: str,
    object_type: str,
) -> Tuple[str | None, float, str]:

    _build_cache()

    object_type = object_type.upper()

    if object_type not in _embedding_cache:
        raise ValueError(f"Unsupported object type: {object_type}")

    query_vector = np.array(embed(raw_status))

    best_status = None
    best_score = -1.0
    method = "embedding"

    for canonical_status, alias_vectors in _embedding_cache[
        object_type
    ].items():

        for alias, vector in alias_vectors:

            score = float(np.dot(query_vector, vector))

            if score > best_score:
                best_score = score
                best_status = canonical_status

                if alias.lower() == raw_status.lower():
                    method = "alias"

    if best_score < STATUS_MAPPING_THRESHOLD:
        return None, best_score, method

    return best_status, best_score, method
