"""
rag/embeddings.py: the sentence-transformers model shared by retrieval and the semantic cache.

The model loads on first use, so importing the rag modules is cheap and needs no download.
"""

from functools import lru_cache

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL)


def embed(text: str) -> list[float]:
    """Embedding of one text as a plain list of floats."""
    return get_model().encode([text])[0].tolist()
