import hashlib
import json
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from deadwax.agent import tracing
from deadwax.agent.models import EMBEDDING_DIMENSIONS, build_embeddings, embedding_model

CACHE_DIR = Path(".cache") / "embeddings"
BATCH_SIZE = 50
TEXTS_PER_MINUTE = 90
DOCUMENT = "RETRIEVAL_DOCUMENT"
QUERY = "RETRIEVAL_QUERY"


def cache_path(task: str, text: str) -> Path:
    key = json.dumps([embedding_model(), EMBEDDING_DIMENSIONS, task, text])
    return CACHE_DIR / f"{hashlib.sha256(key.encode()).hexdigest()}.json"


def embed(texts: Sequence[str], task: str) -> list[list[float]]:
    paths = [cache_path(task, text) for text in texts]
    missing = [position for position, path in enumerate(paths) if not path.exists()]

    if missing:
        embedder = build_embeddings()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        batches = [missing[s : s + BATCH_SIZE] for s in range(0, len(missing), BATCH_SIZE)]
        for number, batch in enumerate(batches):
            if number:
                time.sleep(BATCH_SIZE * 60 / TEXTS_PER_MINUTE)
            with tracing.embedding(task.casefold(), embedding_model(), len(batch)):
                vectors = embedder.embed_documents([texts[p] for p in batch], task_type=task)
            for position, vector in zip(batch, vectors, strict=True):
                paths[position].write_text(json.dumps(vector), encoding="utf-8")
            if len(batches) > 1:
                done = min((number + 1) * BATCH_SIZE, len(missing))
                print(f"  embedded {done}/{len(missing)}", file=sys.stderr, flush=True)

    return [json.loads(path.read_text(encoding="utf-8")) for path in paths]


def embed_documents(texts: Sequence[str]) -> list[list[float]]:
    return embed(texts, DOCUMENT)


def embed_query(text: str) -> list[float]:
    return embed([text], QUERY)[0]
