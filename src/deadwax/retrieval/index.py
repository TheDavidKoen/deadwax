import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from deadwax.retrieval.chunking import Chunk
from deadwax.retrieval.search import unit

INDEX_FILE = Path(__file__).parent.parent / "data" / "corpus" / "index.jsonl"
DECIMALS = 6


@dataclass(frozen=True)
class Index:
    model: str
    dimensions: int
    built: str
    chunks: tuple[Chunk, ...]
    vectors: tuple[tuple[float, ...], ...]


def write_index(
    path: Path,
    chunks: Sequence[Chunk],
    vectors: Sequence[Sequence[float]],
    model: str,
    dimensions: int,
    built: str,
) -> None:
    if len(chunks) != len(vectors):
        raise ValueError(f"{len(chunks)} chunks but {len(vectors)} vectors")

    header = {"model": model, "dimensions": dimensions, "built": built, "chunks": len(chunks)}
    lines = [json.dumps(header, ensure_ascii=False)]
    for chunk, vector in zip(chunks, vectors, strict=True):
        if len(vector) != dimensions:
            raise ValueError(f"{chunk.id} has {len(vector)} dimensions, expected {dimensions}")
        record = {**asdict(chunk), "vector": [round(x, DECIMALS) for x in unit(vector)]}
        lines.append(json.dumps(record, ensure_ascii=False))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def read_index(path: Path = INDEX_FILE) -> Index:
    header_line, *record_lines = path.read_text(encoding="utf-8").splitlines()
    header = json.loads(header_line)
    records = [json.loads(line) for line in record_lines]
    return Index(
        model=header["model"],
        dimensions=header["dimensions"],
        built=header["built"],
        chunks=tuple(Chunk(**{k: v for k, v in r.items() if k != "vector"}) for r in records),
        vectors=tuple(tuple(r["vector"]) for r in records),
    )
