_model = None
MODEL_NAME = "all-MiniLM-L6-v2"  # 384-dim, fast, good semantic quality


def load():
    global _model
    try:
        from sentence_transformers import SentenceTransformer
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "sentence-transformers is required for embeddings. "
            "Install dependencies with: pip install -r requirements.txt"
        ) from exc

    _model = SentenceTransformer(MODEL_NAME)


def embed(text: str) -> list[float]:
    if _model is None:
        raise RuntimeError("Embedder not loaded - call embedder.load() at startup")
    return _model.encode(text, normalize_embeddings=True).tolist()
