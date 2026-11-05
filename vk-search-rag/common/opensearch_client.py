"""
Всё взаимодействие с OpenSearch: создание индекса (BM25-поле + knn_vector-поле),
создание search pipeline для гибридного поиска (нормализация + объединение
скоров BM25 и kNN), сам гибридный поиск и bulk-индексация документов.

Гибридный поиск реализован через нативный механизм OpenSearch 2.10+:
query-тип "hybrid" + search pipeline с normalization-processor.
Документация: https://docs.opensearch.org/latest/search-plugins/hybrid-search/
"""
from opensearchpy import OpenSearch, helpers

from common.config import settings


def get_client() -> OpenSearch:
    return OpenSearch(
        hosts=[{"host": settings.OPENSEARCH_HOST, "port": settings.OPENSEARCH_PORT}],
        http_auth=(settings.OPENSEARCH_USER, settings.OPENSEARCH_PASSWORD),
        use_ssl=settings.OPENSEARCH_USE_SSL,
        verify_certs=False,
        ssl_show_warn=False,
    )


INDEX_BODY = {
    "settings": {
        "index": {
            "knn": True,
            "number_of_shards": 1,
            "number_of_replicas": 0,
        }
    },
    "mappings": {
        "properties": {
            "post_id": {"type": "keyword"},
            "chunk_id": {"type": "keyword"},
            "url": {"type": "keyword"},
            "date": {"type": "date", "format": "epoch_second"},
            "likes": {"type": "integer"},
            "reposts": {"type": "integer"},
            "views": {"type": "integer"},
            "text": {
                "type": "text",
                "analyzer": "russian",  # встроенный в OpenSearch анализатор для BM25 по-русски
            },
            "embedding": {
                "type": "knn_vector",
                "dimension": settings.EMBEDDING_DIM,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "lucene",
                    "parameters": {"ef_construction": 128, "m": 24},
                },
            },
        }
    },
}


def create_index(client: OpenSearch, force: bool = False):
    exists = client.indices.exists(index=settings.INDEX_NAME)
    if exists and force:
        client.indices.delete(index=settings.INDEX_NAME)
        exists = False
    if not exists:
        client.indices.create(index=settings.INDEX_NAME, body=INDEX_BODY)
        print(f"Индекс '{settings.INDEX_NAME}' создан.")
    else:
        print(f"Индекс '{settings.INDEX_NAME}' уже существует, пропускаю создание.")


def create_search_pipeline(client: OpenSearch):
    """
    normalization-processor приводит BM25-скор и kNN-скор (разные шкалы!)
    к сопоставимому диапазону (min_max), затем комбинирует взвешенной суммой
    (arithmetic_mean с весами HYBRID_WEIGHT_BM25 / HYBRID_WEIGHT_KNN).
    """
    pipeline_body = {
        "description": "Hybrid BM25 + kNN normalization pipeline",
        "phase_results_processors": [
            {
                "normalization-processor": {
                    "normalization": {"technique": "min_max"},
                    "combination": {
                        "technique": "arithmetic_mean",
                        "parameters": {
                            "weights": [
                                settings.HYBRID_WEIGHT_BM25,
                                settings.HYBRID_WEIGHT_KNN,
                            ]
                        },
                    },
                }
            }
        ],
    }
    client.transport.perform_request(
        "PUT",
        f"/_search/pipeline/{settings.SEARCH_PIPELINE}",
        body=pipeline_body,
    )
    print(f"Search pipeline '{settings.SEARCH_PIPELINE}' создан/обновлён.")


def bulk_index(client: OpenSearch, documents: list[dict]):
    """documents: список готовых к индексации doc'ов (с полем 'embedding')."""
    actions = [
        {
            "_index": settings.INDEX_NAME,
            "_id": doc["chunk_id"],
            "_source": doc,
        }
        for doc in documents
    ]
    helpers.bulk(client, actions)


def hybrid_search(client: OpenSearch, query_text: str, query_vector: list[float], top_n: int) -> list[dict]:
    body = {
        "size": top_n,
        "_source": ["post_id", "url", "text", "date", "likes"],
        "query": {
            "hybrid": {
                "queries": [
                    {"match": {"text": {"query": query_text}}},
                    {"knn": {"embedding": {"vector": query_vector, "k": top_n}}},
                ]
            }
        },
    }
    resp = client.transport.perform_request(
        "GET",
        f"/{settings.INDEX_NAME}/_search?search_pipeline={settings.SEARCH_PIPELINE}",
        body=body,
    )
    hits = resp.get("hits", {}).get("hits", [])
    results = []
    for h in hits:
        src = h["_source"]
        results.append(
            {
                "score": h["_score"],
                "post_id": src.get("post_id"),
                "url": src.get("url"),
                "text": src.get("text"),
                "date": src.get("date"),
                "likes": src.get("likes"),
            }
        )
    return results
