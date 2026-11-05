"""
RAG-суммаризация: получаем top-N найденных чанков и просим LLM ответить
на вопрос пользователя строго на их основе.

Поддержаны три провайдера через LLM_PROVIDER в .env:
- openai   — любой OpenAI-совместимый эндпоинт (OpenAI, прокси и т.п.)
- anthropic
- ollama   — локальная модель без внешнего API

Ключевой момент по заданию: в системный промпт жёстко зашита инструкция
не придумывать ответ, если документы не отвечают на вопрос.
"""
import requests

from common.config import settings

SYSTEM_PROMPT = (
    "Ты — ассистент поиска. Отвечай на вопрос пользователя ТОЛЬКО на основе "
    "документов, приложенных ниже. Если документы не отвечают на вопрос "
    "пользователя — прямо скажи об этом, не придумывай ответ и не используй "
    "знания вне предоставленных документов. В конце ответа кратко укажи, "
    "на какие документы (по номеру) ты опирался."
)


def build_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        parts.append(f"[Документ {i}] (ссылка: {c.get('url')})\n{c.get('text')}")
    return "\n\n".join(parts)


def build_user_prompt(query: str, chunks: list[dict]) -> str:
    context = build_context(chunks)
    return f"Документы:\n\n{context}\n\nВопрос пользователя: {query}"


def _call_openai(system: str, user: str) -> str:
    base_url = settings.LLM_BASE_URL or "https://api.openai.com/v1"
    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
        json={
            "model": settings.LLM_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_anthropic(system: str, user: str) -> str:
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": settings.LLM_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": settings.LLM_MODEL,
            "max_tokens": 1024,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    content = resp.json()["content"]
    return "".join(block.get("text", "") for block in content)


def _call_ollama(system: str, user: str) -> str:
    resp = requests.post(
        f"{settings.OLLAMA_HOST}/api/chat",
        json={
            "model": settings.LLM_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


_PROVIDERS = {
    "openai": _call_openai,
    "anthropic": _call_anthropic,
    "ollama": _call_ollama,
}


def get_llm_answer(query: str, chunks: list[dict]) -> str:
    if not chunks:
        return "По вашему запросу ничего не найдено в базе документов."

    user_prompt = build_user_prompt(query, chunks)
    fn = _PROVIDERS.get(settings.LLM_PROVIDER)
    if fn is None:
        raise ValueError(f"Неизвестный LLM_PROVIDER: {settings.LLM_PROVIDER}")
    return fn(SYSTEM_PROMPT, user_prompt)
