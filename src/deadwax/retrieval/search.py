import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Hit:
    position: int
    score: float


def unit(vector: Sequence[float]) -> list[float]:
    norm = math.hypot(*vector)
    if norm == 0:
        raise ValueError("cannot normalise a zero vector")
    return [x / norm for x in vector]


def top_k(query: Sequence[float], unit_vectors: Sequence[Sequence[float]], k: int) -> list[Hit]:
    direction = unit(query)
    hits = [
        Hit(position, math.sumprod(direction, vector))
        for position, vector in enumerate(unit_vectors)
    ]
    return sorted(hits, key=lambda hit: hit.score, reverse=True)[:k]
