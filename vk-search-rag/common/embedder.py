"""
Обёртка над эмбеддером. Модель по умолчанию — intfloat/multilingual-e5-base:
- многоязычная, хорошо работает с русским текстом
- асимметричная (E5): документы и запросы кодируются с разными префиксами
  ("passage: " для документов, "query: " для запросов) — это требование
  архитектуры E5, без него качество поиска заметно хуже.

Модель кэшируется как синглтон, чтобы не грузить веса на каждый вызов.
"""
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from common.config import settings


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def embed_documents(texts: list[str]) -> list[list[float]]:
    model = _get_model()
    prefixed = [f"passage: {t}" for t in texts]
    vectors = model.encode(
        prefixed,
        batch_size=32,
        show_progress_bar=len(texts) > 100,
        normalize_embeddings=True,  # для cosinesimil в OpenSearch важна нормировка
    )
    return np.asarray(vectors).tolist()


def embed_query(text: str) -> list[float]:
    model = _get_model()
    vector = model.encode(f"query: {text}", normalize_embeddings=True)
    return np.asarray(vector).tolist()
