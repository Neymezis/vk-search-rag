import argparse
import json
from pathlib import Path

from tqdm import tqdm

from common.chunker import chunk_text
from common.embedder import embed_documents
from common.opensearch_client import get_client, create_index, create_search_pipeline, bulk_index

EMBED_BATCH_SIZE = 64


def load_posts(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def build_chunk_docs(posts) -> list[dict]:
    docs = []
    for post in posts:
        chunks = chunk_text(post["text"])
        for i, chunk in enumerate(chunks):
            docs.append(
                {
                    "chunk_id": f"{post['post_id']}_{i}",
                    "post_id": post["post_id"],
                    "url": post["url"],
                    "date": post.get("date"),
                    "likes": post.get("likes", 0),
                    "reposts": post.get("reposts", 0),
                    "views": post.get("views", 0),
                    "text": chunk,
                }
            )
    return docs


def index_all(in_path: Path, force_recreate: bool = False):
    client = get_client()
    create_index(client, force=force_recreate)
    create_search_pipeline(client)

    posts = list(load_posts(in_path))
    print(f"Загружено постов: {len(posts)}")

    chunk_docs = build_chunk_docs(posts)
    print(f"Получено чанков для индексации: {len(chunk_docs)}")

    for i in tqdm(range(0, len(chunk_docs), EMBED_BATCH_SIZE), desc="Индексация"):
        batch = chunk_docs[i:i + EMBED_BATCH_SIZE]
        texts = [d["text"] for d in batch]
        vectors = embed_documents(texts)
        for doc, vec in zip(batch, vectors):
            doc["embedding"] = vec
        bulk_index(client, batch)

    client.indices.refresh(index="vk_documents")
    print("Индексация завершена.")


def main():
    parser = argparse.ArgumentParser(description="Индексация постов в OpenSearch")
    parser.add_argument("--in", dest="in_path", default="data/raw_posts.jsonl")
    parser.add_argument("--force-recreate", action="store_true", help="пересоздать индекс с нуля")
    args = parser.parse_args()

    index_all(Path(args.in_path), force_recreate=args.force_recreate)


if __name__ == "__main__":
    main()
