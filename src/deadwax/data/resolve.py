import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

MIN_CONFIDENT_SCORE = 95
ALTERNATIVES_SHOWN = 3
CURLY_APOSTROPHE = "\N{RIGHT SINGLE QUOTATION MARK}"


@dataclass(frozen=True)
class Candidate:
    mbid: str
    name: str
    disambiguation: str
    score: int
    country: str | None
    tags: tuple[str, ...]


@dataclass(frozen=True)
class Resolution:
    artist: str
    chosen: Candidate | None
    alternatives: tuple[Candidate, ...]
    reason: str | None

    @property
    def needs_review(self) -> bool:
        return self.reason is not None


def normalise(name: str) -> str:
    decomposed = unicodedata.normalize("NFKD", name.replace(CURLY_APOSTROPHE, "'"))
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold().strip()


def to_candidate(raw: Mapping) -> Candidate:
    return Candidate(
        mbid=raw["id"],
        name=raw["name"],
        disambiguation=raw.get("disambiguation", ""),
        score=int(raw.get("score", 0)),
        country=raw.get("country"),
        tags=tuple(sorted(tag["name"] for tag in raw.get("tags", []))),
    )


def tag_overlap(candidate: Candidate, genres: Iterable[str]) -> int:
    wanted = {normalise(genre) for genre in genres}
    return sum(1 for tag in candidate.tags if normalise(tag) in wanted)


def resolve(artist: str, genres: Sequence[str], results: Sequence[Mapping]) -> Resolution:
    candidates = [to_candidate(raw) for raw in results]
    if not candidates:
        return Resolution(artist, None, (), "MusicBrainz returned no results")

    exact = [c for c in candidates if normalise(c.name) == normalise(artist)]
    pool = exact or candidates
    ranked = sorted(pool, key=lambda c: (tag_overlap(c, genres), c.score), reverse=True)
    chosen, others = ranked[0], ranked[1:]

    if not exact:
        reason = f"no exact name match; the closest result is {chosen.name!r}"
    elif len(exact) > 1:
        separated = tag_overlap(chosen, genres) > tag_overlap(others[0], genres)
        how = "picked by genre tags" if separated else "genre tags do not separate them"
        reason = f"{len(exact)} artists share this name; {how}"
    elif chosen.score < MIN_CONFIDENT_SCORE:
        reason = f"search score is only {chosen.score}"
    else:
        reason = None

    return Resolution(artist, chosen, tuple(others[:ALTERNATIVES_SHOWN]), reason)
