from collections.abc import Iterable, Mapping, Sequence

GENRES_PER_ARTIST = 3


def credited_artists(recordings: Iterable[Mapping]) -> list[str]:
    ids = (
        credit["artist"]["id"]
        for recording in recordings
        for credit in recording.get("artist-credit", [])
        if credit.get("artist", {}).get("id")
    )
    return list(dict.fromkeys(ids))


def top_genres(artist: Mapping, limit: int = GENRES_PER_ARTIST) -> list[str]:
    ranked = sorted(artist.get("genres", []), key=lambda g: (-g.get("count", 0), g["name"]))
    return [genre["name"] for genre in ranked[:limit]]


def pooled(genre_lists: Iterable[Sequence[str]]) -> list[str]:
    return list(dict.fromkeys(genre for genres in genre_lists for genre in genres))
