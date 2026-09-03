from dataclasses import dataclass
from enum import StrEnum


class ViolationCode(StrEnum):
    DURATION_OVER = "DURATION_OVER"
    DURATION_UNDER = "DURATION_UNDER"
    TRACK_TOO_LONG = "TRACK_TOO_LONG"
    ARTIST_LIMIT_EXCEEDED = "ARTIST_LIMIT_EXCEEDED"
    RELEASE_YEAR_OUT_OF_RANGE = "RELEASE_YEAR_OUT_OF_RANGE"
    GENRE_NOT_ALLOWED = "GENRE_NOT_ALLOWED"
    DUPLICATE_TRACK = "DUPLICATE_TRACK"


class InfeasibleReason(StrEnum):
    NO_CANDIDATE_TRACKS = "NO_CANDIDATE_TRACKS"
    INSUFFICIENT_TOTAL_DURATION = "INSUFFICIENT_TOTAL_DURATION"


@dataclass(frozen=True)
class Constraints:
    min_total_duration_ms: int | None = None
    max_total_duration_ms: int | None = None
    max_track_duration_ms: int | None = None
    max_tracks_per_artist: int | None = None
    released_before: int | None = None
    released_after: int | None = None
    required_genres: tuple[str, ...] = ()
    target_energy: float | None = None


@dataclass(frozen=True)
class Violation:
    code: ViolationCode
    track_ids: tuple[str, ...]
    remedy: str
    adjust_by: int | None = None


@dataclass(frozen=True)
class SoftScore:
    name: str
    score: float
    provenance: str


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    violations: tuple[Violation, ...]
    soft_scores: tuple[SoftScore, ...]


@dataclass(frozen=True)
class Feasibility:
    feasible: bool
    reason: InfeasibleReason | None
    candidate_count: int
    max_achievable_ms: int
    requested_min_ms: int
