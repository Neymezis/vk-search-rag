import argparse
import json
import re
import time
from pathlib import Path

import requests

from common.config import settings

VK_API_URL = "https://api.vk.com/method/wall.get"
REQUEST_DELAY_SEC = 0.35  
BATCH_SIZE = 100  


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def fetch_batch(domain: str, offset: int, token: str, api_version: str) -> dict:
    params = {
        "domain": domain,
        "count": BATCH_SIZE,
        "offset": offset,
        "access_token": token,
        "v": api_version,
        "filter": "owner",  
    }
    resp = requests.get(VK_API_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"VK API error: {data['error']}")
    return data["response"]


def post_to_doc(post: dict) -> dict | None:
    text = clean_text(post.get("text", ""))
    if not text or len(text) < 40:
        return None
    owner_id = post["owner_id"]
    post_id = post["id"]
    return {
        "post_id": f"{owner_id}_{post_id}",
        "text": text,
        "date": post.get("date"), 
        "url": f"https://vk.com/wall{owner_id}_{post_id}",
        "likes": post.get("likes", {}).get("count", 0),
        "reposts": post.get("reposts", {}).get("count", 0),
        "views": post.get("views", {}).get("count", 0),
    }


def parse_group(domain: str, max_posts: int, token: str, api_version: str, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)

    collected = 0
    offset = 0
    seen_ids = set()

    if out_path.exists():
        with out_path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    doc = json.loads(line)
                    seen_ids.add(doc["post_id"])
                except Exception:
                    continue
        collected = len(seen_ids)
        offset = collected
        print(f"Найден существующий файл, уже собрано {collected} документов. Продолжаем с offset={offset}.")

    with out_path.open("a", encoding="utf-8") as f:
        while collected < max_posts:
            try:
                batch = fetch_batch(domain, offset, token, api_version)
            except RuntimeError as e:
                print(f"Ошибка VK API: {e}. Останавливаюсь.")
                break

            items = batch.get("items", [])
            if not items:
                print("Больше постов нет, паблик исчерпан.")
                break

            for post in items:
                doc = post_to_doc(post)
                if doc is None or doc["post_id"] in seen_ids:
                    continue
                seen_ids.add(doc["post_id"])
                f.write(json.dumps(doc, ensure_ascii=False) + "\n")
                collected += 1

            offset += BATCH_SIZE
            print(f"Собрано: {collected}/{max_posts} (offset={offset})")
            time.sleep(REQUEST_DELAY_SEC)

    print(f"Готово. Итого документов: {collected}. Файл: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Парсинг паблика VK в JSONL")
    parser.add_argument("--domain", default=settings.VK_GROUP_DOMAIN, help="короткое имя паблика (без vk.com/)")
    parser.add_argument("--count", type=int, default=settings.VK_MAX_POSTS, help="сколько постов собрать")
    parser.add_argument("--out", default="data/raw_posts.jsonl", help="путь к выходному jsonl файлу")
    args = parser.parse_args()

    if not settings.VK_API_TOKEN:
        raise SystemExit("VK_API_TOKEN не задан в .env")
    if not args.domain:
        raise SystemExit("Не указан --domain (или VK_GROUP_DOMAIN в .env)")

    parse_group(
        domain=args.domain,
        max_posts=args.count,
        token=settings.VK_API_TOKEN,
        api_version=settings.VK_API_VERSION,
        out_path=Path(args.out),
    )


if __name__ == "__main__":
    main()
