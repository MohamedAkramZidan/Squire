"""
services/embedder.py

Shared Embedding Service
=========================

A thread-safe, lazily-initialized, singleton wrapper around a
sentence-transformers model that produces normalized fixed-dimension
embeddings for use across the entire backend (RAG Retriever, Status
Mapper, Cache Layer, semantic search over pgvector, etc.).

Design goals
------------
1. The underlying ML model is expensive to load (disk + memory + CPU/GPU
   warm-up). It must be loaded exactly once per process and reused for
   every subsequent call, regardless of how many modules import this
   file or how many requests are served concurrently.
2. The public API is intentionally small and framework-agnostic so it
   can be called from FastAPI/Flask request handlers, Celery workers,
   CLI scripts, or batch jobs without any extra wiring.
3. All embeddings are L2-normalized so that downstream consumers can use
   plain dot-product similarity (equivalent to cosine similarity) when
   querying pgvector or any other vector store.

Environment variables
----------------------
EMBEDDING_MODEL   Name (or path) of the sentence-transformers model to
                   load. Defaults to "all-MiniLM-L6-v2".
EMBEDDING_DIM      Expected output embedding dimensionality. Defaults to
                   384. Used purely as a sanity check against the model
                   actually loaded; if they don't match, a
                   ``EmbeddingDimensionMismatchError`` is raised at load
                   time so misconfiguration is caught early instead of
                   silently corrupting vector-store data.
EMBEDDING_DEVICE   Optional. "cpu", "cuda", or "mps". If unset,
                   sentence-transformers will auto-select.

Typical usage
-------------
    from services.embedder import embed, embed_batch

    vector = embed("finish report")          # list[float], len == 384
    vectors = embed_batch(["a", "b", "c"])    # list[list[float]]

The module also exposes a class-based API (``EmbeddingService``) for
cases where dependency injection or test isolation is preferred over
the module-level singleton functions.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Final, List, Optional, Sequence

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration defaults (overridable via environment variables)
# ---------------------------------------------------------------------------
DEFAULT_MODEL_NAME: Final[str] = "all-MiniLM-L6-v2"
DEFAULT_EMBEDDING_DIM: Final[int] = 384


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class EmbeddingServiceError(Exception):
    """Base exception for all embedding-service related failures."""


class ModelLoadError(EmbeddingServiceError):
    """Raised when the underlying sentence-transformers model fails to load."""


class EmbeddingDimensionMismatchError(EmbeddingServiceError):
    """Raised when the loaded model's output dimension does not match
    the dimension configured via ``EMBEDDING_DIM``.
    """


class InvalidInputError(EmbeddingServiceError):
    """Raised when the caller supplies invalid input (empty string, wrong
    type, empty batch, non-string items, etc.).
    """


# ---------------------------------------------------------------------------
# Core service
# ---------------------------------------------------------------------------
class EmbeddingService:
    """Thread-safe, lazily-loaded wrapper around a sentence-transformers model.

    The class itself is not a singleton -- instantiate it directly when you
    need an isolated instance (e.g. in unit tests, or to load a different
    model). For the common case of "one shared model per process", use the
    module-level convenience functions (:func:`load`, :func:`embed`,
    :func:`embed_batch`, etc.) which operate on a process-wide singleton
    instance of this class.

    Thread safety
    --------------
    Model loading is guarded by a ``threading.Lock`` using the standard
    double-checked-locking pattern, so concurrent requests arriving before
    the model has finished loading will not trigger multiple redundant
    loads, and will not race on partially-initialized state.

    Parameters
    ----------
    model_name:
        Name or local path of the sentence-transformers model to load.
        Defaults to the ``EMBEDDING_MODEL`` environment variable, falling
        back to :data:`DEFAULT_MODEL_NAME`.
    expected_dim:
        The embedding dimensionality this model is expected to produce.
        Defaults to the ``EMBEDDING_DIM`` environment variable, falling
        back to :data:`DEFAULT_EMBEDDING_DIM`. Used as a sanity check at
        load time.
    device:
        Optional device override ("cpu", "cuda", "mps"). Defaults to the
        ``EMBEDDING_DEVICE`` environment variable, or ``None`` (meaning
        sentence-transformers will auto-select the best available device).
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        expected_dim: Optional[int] = None,
        device: Optional[str] = None,
    ) -> None:
        self._model_name: str = model_name or os.getenv(
            "EMBEDDING_MODEL", DEFAULT_MODEL_NAME
        )
        self._expected_dim: int = int(
            expected_dim
            if expected_dim is not None
            else os.getenv("EMBEDDING_DIM", DEFAULT_EMBEDDING_DIM)
        )
        self._device: Optional[str] = device or os.getenv("EMBEDDING_DEVICE") or None

        self._model = None  # lazily populated SentenceTransformer instance
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def load(self) -> None:
        """Load the sentence-transformers model into memory, if not already loaded.

        This method is idempotent and thread-safe: calling it multiple
        times (sequentially or concurrently from multiple threads) results
        in exactly one model load. All embedding calls implicitly invoke
        this method, so explicit calls are optional but useful for warming
        up the model eagerly at application startup (e.g. in a FastAPI
        ``lifespan``/``startup`` event) to avoid latency on the first
        real request.

        Raises
        ------
        ModelLoadError
            If the underlying library cannot be imported or the model
            fails to download/initialize.
        EmbeddingDimensionMismatchError
            If the loaded model's native output dimension does not match
            the configured ``expected_dim``.
        """
        if self._model is not None:
            return

        with self._lock:
            # Double-checked locking: another thread may have finished
            # loading while we were waiting for the lock.
            if self._model is not None:
                return

            logger.info(
                "Loading embedding model '%s' (device=%s)...",
                self._model_name,
                self._device or "auto",
            )

            try:
                # Imported lazily so that importing this module never
                # requires sentence-transformers to be installed unless
                # the model is actually used (keeps lightweight tooling,
                # e.g. linters or unrelated unit tests, fast and free of
                # heavy ML dependencies).
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:  # pragma: no cover - environment issue
                raise ModelLoadError(
                    "The 'sentence-transformers' package is required to use "
                    "EmbeddingService. Install it with: "
                    "pip install sentence-transformers"
                ) from exc

            try:
                model = SentenceTransformer(self._model_name, device=self._device)
            except Exception as exc:  # noqa: BLE001 - surfaced as ModelLoadError
                raise ModelLoadError(
                    f"Failed to load embedding model '{self._model_name}': {exc}"
                ) from exc

            actual_dim = model.get_sentence_embedding_dimension()
            if actual_dim != self._expected_dim:
                raise EmbeddingDimensionMismatchError(
                    f"Loaded model '{self._model_name}' produces embeddings of "
                    f"dimension {actual_dim}, but EMBEDDING_DIM is configured "
                    f"as {self._expected_dim}. Update EMBEDDING_DIM or choose "
                    f"a matching model."
                )

            self._model = model
            logger.info(
                "Embedding model '%s' loaded successfully (dim=%d, device=%s).",
                self._model_name,
                actual_dim,
                self._device or "auto",
            )

    @property
    def is_loaded(self) -> bool:
        """Return ``True`` if the underlying model has already been loaded."""
        return self._model is not None

    # ------------------------------------------------------------------
    # Embedding generation
    # ------------------------------------------------------------------
    def embed(self, text: str) -> List[float]:
        """Generate a normalized embedding vector for a single text string.

        Parameters
        ----------
        text:
            The input text to embed. Must be a non-empty string (after
            stripping whitespace).

        Returns
        -------
        list[float]
            A normalized embedding vector of length ``get_embedding_dimension()``.

        Raises
        ------
        InvalidInputError
            If ``text`` is not a string, or is empty/whitespace-only.
        ModelLoadError
            If the model fails to load.
        """
        if not isinstance(text, str):
            raise InvalidInputError(
                f"embed() expects a str, got {type(text).__name__}."
            )
        if not text.strip():
            raise InvalidInputError("embed() received an empty or whitespace-only string.")

        self.load()

        try:
            vector = self._model.encode(
                text,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
        except Exception as exc:  # noqa: BLE001
            raise EmbeddingServiceError(f"Failed to compute embedding: {exc}") from exc

        return vector.astype(float).tolist()

    def embed_batch(
        self,
        texts: Sequence[str],
        batch_size: int = 32,
        show_progress_bar: bool = False,
    ) -> List[List[float]]:
        """Generate normalized embedding vectors for a batch of text strings.

        Batch encoding is substantially faster per-item than calling
        :meth:`embed` in a loop, because sentence-transformers can group
        inputs into tensor batches and exploit vectorized computation
        (and GPU parallelism, when available).

        Parameters
        ----------
        texts:
            A non-empty sequence of non-empty strings.
        batch_size:
            Number of texts encoded per internal batch. Tune this based on
            available memory/GPU; 32 is a safe default for CPU inference.
        show_progress_bar:
            Whether to display a tqdm progress bar (useful for large
            offline backfill jobs, should stay ``False`` in request-serving
            code paths).

        Returns
        -------
        list[list[float]]
            One normalized embedding vector per input text, in the same
            order as ``texts``.

        Raises
        ------
        InvalidInputError
            If ``texts`` is empty, not a sequence, or contains any
            non-string or empty/whitespace-only items.
        ModelLoadError
            If the model fails to load.
        """
        if not isinstance(texts, (list, tuple)):
            raise InvalidInputError(
                f"embed_batch() expects a list or tuple of str, got {type(texts).__name__}."
            )
        if len(texts) == 0:
            raise InvalidInputError("embed_batch() received an empty list of texts.")

        for i, item in enumerate(texts):
            if not isinstance(item, str):
                raise InvalidInputError(
                    f"embed_batch() item at index {i} is not a str "
                    f"(got {type(item).__name__})."
                )
            if not item.strip():
                raise InvalidInputError(
                    f"embed_batch() item at index {i} is empty or whitespace-only."
                )

        self.load()

        try:
            vectors = self._model.encode(
                list(texts),
                batch_size=batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=show_progress_bar,
            )
        except Exception as exc:  # noqa: BLE001
            raise EmbeddingServiceError(f"Failed to compute batch embeddings: {exc}") from exc

        return vectors.astype(float).tolist()

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    def get_embedding_dimension(self) -> int:
        """Return the configured/expected embedding dimensionality (e.g. 384)."""
        return self._expected_dim

    def get_model_name(self) -> str:
        """Return the name of the sentence-transformers model in use."""
        return self._model_name


# ---------------------------------------------------------------------------
# Process-wide singleton + module-level convenience API
# ---------------------------------------------------------------------------
_singleton_lock = threading.Lock()
_singleton_instance: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Return the process-wide :class:`EmbeddingService` singleton, creating
    it on first call. Thread-safe.

    Other modules (Status Mapper, RAG Retriever, Cache Layer, ...) should
    generally prefer the flat module-level functions (:func:`embed`,
    :func:`embed_batch`, etc.) below, but this accessor is provided for
    advanced cases such as dependency injection in tests.
    """
    global _singleton_instance
    if _singleton_instance is None:
        with _singleton_lock:
            if _singleton_instance is None:
                _singleton_instance = EmbeddingService()
    return _singleton_instance


def load() -> None:
    """Eagerly load the shared embedding model.

    Call this once at application startup (e.g. FastAPI startup event) to
    avoid paying the model-load latency on the first incoming request.
    Safe to call multiple times; subsequent calls are no-ops.
    """
    get_embedding_service().load()


def embed(text: str) -> List[float]:
    """Generate a normalized embedding for a single string using the shared
    process-wide model.

    See :meth:`EmbeddingService.embed` for full documentation.
    """
    return get_embedding_service().embed(text)


def embed_batch(
    texts: Sequence[str],
    batch_size: int = 32,
    show_progress_bar: bool = False,
) -> List[List[float]]:
    """Generate normalized embeddings for a batch of strings using the
    shared process-wide model.

    See :meth:`EmbeddingService.embed_batch` for full documentation.
    """
    return get_embedding_service().embed_batch(
        texts, batch_size=batch_size, show_progress_bar=show_progress_bar
    )


def get_embedding_dimension() -> int:
    """Return the configured embedding dimensionality of the shared model."""
    return get_embedding_service().get_embedding_dimension()


def get_model_name() -> str:
    """Return the name of the shared model in use."""
    return get_embedding_service().get_model_name()


def reset_singleton_for_testing() -> None:
    """Reset the process-wide singleton.

    Intended for use in test suites only, so that each test can verify
    fresh-loading behavior without leaking state between tests. Not
    intended to be called from application code.
    """
    global _singleton_instance
    with _singleton_lock:
        _singleton_instance = None
