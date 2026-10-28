import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime

from deadwax.data.fixtures import Track

ISRC = re.compile(r"[A-Z]{2}[A-Z0-9]{3}[0-9]{7}")


@dataclass(frozen=True)
class Pulled:
    tracks: tuple[Track, ...]
    skipped: tuple[str, ...]


def release_year(album: Mapping) -> int | None:
    year = (album.get("release_date") or "")[:4]
    return int(year) if year.isdigit() and int(year) > 0 else None


def last_played(recent: Iterable[Mapping]) -> dict[str, date]:
    played: dict[str, date] = {}
    for item in recent:
        track_id = item["track"]["id"]
        when = datetime.fromisoformat(item["played_at"]).date()
        played[track_id] = max(when, played.get(track_id, when))
    return played


def isrc(item: Mapping) -> str | None:
    raw = (item["track"].get("external_ids") or {}).get("isrc") or ""
    code = raw.replace("-", "").replace(" ", "").upper()
    return code if ISRC.fullmatch(code) else None


def to_track(
    item: Mapping, genres_by_track: Mapping[str, Sequence[str]], played: Mapping[str, date]
) -> Track | None:
    track = item["track"]
    year = release_year(track.get("album", {}))
    if track.get("is_local") or not track.get("id") or year is None:
        return None
    return Track(
        id=track["id"],
        name=track["name"],
        artists=tuple(a["name"] for a in track["artists"]),
        duration_ms=track["duration_ms"],
        genres=tuple(genres_by_track.get(track["id"], ())),
        release_year=year,
        energy=None,
        added_at=datetime.fromisoformat(item["added_at"]).date(),
        last_played_at=played.get(track["id"]),
    )


def build_library(
    saved: Iterable[Mapping],
    genres_by_track: Mapping[str, Sequence[str]],
    played: Mapping[str, date],
) -> Pulled:
    tracks: dict[str, Track] = {}
    skipped: list[str] = []
    for item in saved:
        track = to_track(item, genres_by_track, played)
        if track is None:
            skipped.append(item["track"].get("name") or "unnamed track")
        else:
            tracks.setdefault(track.id, track)
    return Pulled(tuple(tracks.values()), tuple(skipped))
