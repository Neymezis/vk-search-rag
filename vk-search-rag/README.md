# VK Search & RAG

Поисковик по паблику VK с гибридным поиском (BM25 + векторный kNN в OpenSearch)
и RAG-суммаризацией ответа через LLM.

## Архитектура

```
Client ──get_api──> API (FastAPI)
                       │
                       ├─ /search ──> OpenSearch (hybrid: BM25 + kNN) ──> top-N чанков со score
                       │
                       └─ /ask ────> /search (top 3-5) ──> LLM (summarize) ──> ответ + источники
```

Компоненты:

| Модуль | Назначение |
|---|---|
| `parser/vk_parser.py` | Парсинг постов паблика VK через `wall.get`, сохранение в `data/raw_posts.jsonl` |
| `common/chunker.py` | Разбиение длинных постов на чанки с overlap |
| `common/embedder.py` | Эмбеддинги текста (`intfloat/multilingual-e5-base`) |
| `common/opensearch_client.py` | Индекс, hybrid search pipeline, bulk-загрузка, гибридный поиск |
| `indexer/index_documents.py` | Пайплайн: raw posts → chunks → embeddings → OpenSearch |
| `common/llm.py` | RAG-суммаризация (OpenAI / Anthropic / Ollama — на выбор) |
| `app/main.py` | FastAPI: `/health`, `/search`, `/ask` |

## Схема документа в индексе (ER)

Один документ в OpenSearch = один чанк текста поста.

```
Post (VK)                          Chunk (индексируемый документ)
──────────                         ──────────────────────────────
post_id  (owner_id_id)   1 ─── N   chunk_id   = "{post_id}_{i}"   PK
text                                post_id    = FK на пост
date                                url
url                                 date
likes                               likes / reposts / views
reposts                             text        (BM25, russian analyzer)
views                               embedding   (knn_vector, dim=768, cosinesimil)
```

Один пост в жизни превращается в 1..N чанков (обычно 1, т.к. посты VK
короткие; длинные режутся на несколько). Все поля денормализованы прямо
в документ чанка — отдельной "таблицы постов" нет, т.к. OpenSearch не
реляционная БД и join'ы не нужны для поиска.

## Как работает гибридный поиск

При запросе одновременно выполняются:
1. **BM25** (`match` по полю `text`, анализатор `russian`)
2. **kNN** (косинусная близость эмбеддинга запроса и эмбеддингов чанков, HNSW)

Оба скора нормализуются (`min_max`) и складываются с весами
`HYBRID_WEIGHT_BM25` / `HYBRID_WEIGHT_KNN` (по умолчанию 0.4 / 0.6) через
`search pipeline` — нативный механизм OpenSearch 2.10+.

## Запуск

### 1. Настроить окружение

```bash
cp .env.example .env
# впишите VK_API_TOKEN, VK_GROUP_DOMAIN, LLM_API_KEY
```

Как получить `VK_API_TOKEN`: создать Standalone-приложение на
https://dev.vk.com , взять сервисный ключ доступа (Service token) —
он подходит для чтения открытых пабликов через `wall.get` без OAuth
пользователя.

### 2. Поднять инфраструктуру

```bash
docker compose up -d opensearch opensearch-dashboards
```

Дождаться healthy: `docker compose ps`

### 3. Спарсить паблик (локально, не в контейнере — проще для отладки)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m parser.vk_parser --domain <имя_паблика> --count 6000
```

Скрипт докачивает данные при повторном запуске (не начинает с нуля).

### 4. Проиндексировать

```bash
python -m indexer.index_documents --in data/raw_posts.jsonl --force-recreate
```

Первый запуск скачает веса модели эмбеддера (~1.1 ГБ), дальше — из кэша.

### 5. Запустить API

Локально:
```bash
uvicorn app.main:app --reload
```

Или в Docker (после того как данные уже в OpenSearch):
```bash
docker compose up -d api
```

### 6. Проверить

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "новости про искусственный интеллект", "top_n": 5}'

curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "что писали про новые модели ИИ на этой неделе?"}'
```

## Возможные расширения (не входят в MVP)

- Ре-ранжирование результатов (cross-encoder поверх top-N)
- Фильтрация поисковой выдачи (по дате, по лайкам, boolean-фильтры)
- Простой веб-UI поверх `/search` и `/ask`
- Roles/auth — не требуется для этого кейса (не HTTP-сервис с пользователями)
