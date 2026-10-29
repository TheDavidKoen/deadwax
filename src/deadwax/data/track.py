from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Inferred:
    value: float
    provenance: str


@dataclass(frozen=True)
class Track:
    id: str
    name: str
    artists: tuple[str, ...]
    duration_ms: int
    genres: tuple[str, ...]
    release_year: int
    energy: Inferred | None
    added_at: date
    last_played_at: date | None
