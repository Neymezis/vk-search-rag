"""
Единая точка конфигурации. Все настройки читаются из переменных окружения (.env).
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ---- VK ----
    VK_API_TOKEN: str = os.getenv("VK_API_TOKEN", "")
    VK_GROUP_DOMAIN: str = os.getenv("VK_GROUP_DOMAIN", "")  # короткое имя паблика, напр. "habr"
    VK_API_VERSION: str = os.getenv("VK_API_VERSION", "5.199")
    VK_MAX_POSTS: int = int(os.getenv("VK_MAX_POSTS", "6000"))

    # ---- OpenSearch ----
    OPENSEARCH_HOST: str = os.getenv("OPENSEARCH_HOST", "localhost")
    OPENSEARCH_PORT: int = int(os.getenv("OPENSEARCH_PORT", "9200"))
    OPENSEARCH_USER: str = os.getenv("OPENSEARCH_USER", "admin")
    OPENSEARCH_PASSWORD: str = os.getenv("OPENSEARCH_PASSWORD", "admin")
    OPENSEARCH_USE_SSL: bool = os.getenv("OPENSEARCH_USE_SSL", "false").lower() == "true"
    INDEX_NAME: str = os.getenv("INDEX_NAME", "vk_documents")
    SEARCH_PIPELINE: str = os.getenv("SEARCH_PIPELINE", "hybrid-search-pipeline")

    # ---- Embeddings ----
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "768"))

    # ---- Chunking ----
    CHUNK_MAX_CHARS: int = int(os.getenv("CHUNK_MAX_CHARS", "800"))
    CHUNK_OVERLAP_CHARS: int = int(os.getenv("CHUNK_OVERLAP_CHARS", "150"))

    # ---- Hybrid search weights (BM25, kNN) ----
    HYBRID_WEIGHT_BM25: float = float(os.getenv("HYBRID_WEIGHT_BM25", "0.4"))
    HYBRID_WEIGHT_KNN: float = float(os.getenv("HYBRID_WEIGHT_KNN", "0.6"))

    # ---- LLM ----
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")  # openai | anthropic | ollama
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")  # для OpenAI-совместимых эндпоинтов
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    # ---- API ----
    DEFAULT_TOP_N: int = int(os.getenv("DEFAULT_TOP_N", "10"))
    ASK_CONTEXT_DOCS: int = int(os.getenv("ASK_CONTEXT_DOCS", "5"))


settings = Settings()
