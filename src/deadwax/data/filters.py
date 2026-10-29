from collections.abc import Iterable

from deadwax.data.track import Track

FILTERS = (
    "genre",
    "artist",
    "min_duration_ms",
    "max_duration_ms",
    "released_before",
    "released_after",
    "played",
)


def select(
    tracks: Iterable[Track],
    genre: str | None = None,
    artist: str | None = None,
    min_duration_ms: int | None = None,
    max_duration_ms: int | None = None,
    released_before: int | None = None,
    released_after: int | None = None,
    played: bool | None = None,
) -> list[Track]:
    return [
        t
        for t in tracks
        if (genre is None or genre.lower() in [g.lower() for g in t.genres])
        and (artist is None or artist.lower() in [a.lower() for a in t.artists])
        and (min_duration_ms is None or t.duration_ms >= min_duration_ms)
        and (max_duration_ms is None or t.duration_ms <= max_duration_ms)
        and (released_before is None or t.release_year < released_before)
        and (released_after is None or t.release_year > released_after)
        and (played is None or (t.last_played_at is not None) == played)
    ]
