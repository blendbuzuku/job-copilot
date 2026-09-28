"""Turn text into embedding vectors, using a small model that runs locally.

The model (~130 MB) is downloaded the first time it's used, then cached.
"""
from functools import lru_cache

from .config import settings


@lru_cache
def _model():
    from fastembed import TextEmbedding  # imported lazily because loading takes a moment

    return TextEmbedding(settings.embedding_model)


def embed(texts: list[str]) -> list[list[float]]:
    return [vec.tolist() for vec in _model().embed(texts)]
