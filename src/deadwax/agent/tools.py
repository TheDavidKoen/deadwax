from langchain_core.tools import tool

from deadwax.data import TRACKS, Track
from deadwax.domain import Constraints, validator

MIN_DURATION_WINDOW_MS = 120_000


def _display(duration_ms: int) -> str:
    return f"{duration_ms // 60_000}:{duration_ms // 1000 % 60:02d}"


def _as_dict(track: Track) -> dict:
    return {
        "id": track.id,
        "name": track.name,
        "artists": list(track.artists),
        "duration_ms": track.duration_ms,
        "duration_display": _display(track.duration_ms),
        "genres": list(track.genres),
        "release_year": track.release_year,
        "last_played_at": track.last_played_at.isoformat() if track.last_played_at else None,
    }


@tool
def query_library(
    genre: str | None = None,
    artist: str | None = None,
    min_duration_ms: int | None = None,
    max_duration_ms: int | None = None,
    released_before: int | None = None,
    released_after: int | None = None,
    limit: int = 20,
) -> dict:
    """Search the user's music library and return matching tracks with their totals.

    Call this before stating any fact about the library. Never estimate a count, a
    duration or a track name from your own knowledge, and never add numbers up
    yourself: use total_matching and total_duration_ms from the result, which are
    computed exactly. The tracks list is truncated to limit entries, so it may be
    shorter than total_matching.

    Quote duration_display when showing a track's length. Never convert duration_ms
    to minutes yourself.
    """
    matches = [
        t
        for t in TRACKS
        if (genre is None or genre.lower() in [g.lower() for g in t.genres])
        and (artist is None or artist.lower() in [a.lower() for a in t.artists])
        and (min_duration_ms is None or t.duration_ms >= min_duration_ms)
        and (max_duration_ms is None or t.duration_ms <= max_duration_ms)
        and (released_before is None or t.release_year < released_before)
        and (released_after is None or t.release_year > released_after)
    ]
    return {
        "total_matching": len(matches),
        "total_duration_ms": sum(t.duration_ms for t in matches),
        "tracks": [_as_dict(t) for t in matches[:limit]],
    }


@tool
def validate_playlist(
    track_ids: list[str],
    min_total_duration_ms: int | None = None,
    max_total_duration_ms: int | None = None,
    max_track_duration_ms: int | None = None,
    max_tracks_per_artist: int | None = None,
    required_genres: list[str] | None = None,
) -> dict:
    """Check a proposed playlist against hard constraints and report every violation.

    Call this before presenting any playlist to the user. Do not judge for yourself
    whether a playlist meets its constraints. Each violation names the offending
    track ids and an adjust_by amount in the constraint's own unit: negative means
    remove that much, positive means add that much. Act on adjust_by rather than
    guessing how much to change.

    When describing the playlist, quote track_count and total_duration_display from
    this result verbatim. Never sum durations yourself and never convert milliseconds
    to minutes yourself.
    """
    by_id = {t.id: t for t in TRACKS}
    unknown = [i for i in track_ids if i not in by_id]
    if unknown:
        return {"ok": False, "unknown_track_ids": unknown}

    if min_total_duration_ms is not None and max_total_duration_ms is not None:
        window = max_total_duration_ms - min_total_duration_ms
        if window < MIN_DURATION_WINDOW_MS:
            target = (min_total_duration_ms + max_total_duration_ms) // 2
            half = MIN_DURATION_WINDOW_MS // 2
            return {
                "ok": False,
                "invalid_constraints": (
                    f"the duration window is {window} ms wide, which is too narrow to satisfy"
                ),
                "remedy": (
                    f"a duration request is approximate: retry with "
                    f"min_total_duration_ms={target - half} and "
                    f"max_total_duration_ms={target + half}"
                ),
            }

    result = validator.validate(
        [by_id[i] for i in track_ids],
        Constraints(
            min_total_duration_ms=min_total_duration_ms,
            max_total_duration_ms=max_total_duration_ms,
            max_track_duration_ms=max_track_duration_ms,
            max_tracks_per_artist=max_tracks_per_artist,
            required_genres=tuple(required_genres or ()),
        ),
    )
    total_ms = sum(by_id[i].duration_ms for i in track_ids)
    return {
        "ok": result.ok,
        "total_duration_ms": total_ms,
        "total_duration_display": _display(total_ms),
        "track_count": len(track_ids),
        "violations": [
            {
                "code": v.code.value,
                "track_ids": list(v.track_ids),
                "remedy": v.remedy,
                "adjust_by": v.adjust_by,
            }
            for v in result.violations
        ],
        "soft_scores": [
            {"name": s.name, "score": s.score, "provenance": s.provenance}
            for s in result.soft_scores
        ],
    }


@tool
def check_feasibility(
    min_total_duration_ms: int | None = None,
    max_track_duration_ms: int | None = None,
    max_tracks_per_artist: int | None = None,
    required_genres: list[str] | None = None,
    released_before: int | None = None,
    released_after: int | None = None,
) -> dict:
    """Check whether a playlist brief is possible at all, before choosing any tracks.

    Call this first, before query_library, whenever the user asks for a playlist with
    constraints. If feasible is false the brief cannot be satisfied by this library:
    tell the user which constraint fails and stop. Do not build a playlist anyway, do
    not relax the constraint yourself, and do not try alternative track combinations.

    max_achievable_ms is the longest playlist the library can produce under these
    constraints. Compare it against what the user asked for when explaining a refusal.
    """
    outcome = validator.check_feasibility(
        TRACKS,
        Constraints(
            min_total_duration_ms=min_total_duration_ms,
            max_track_duration_ms=max_track_duration_ms,
            max_tracks_per_artist=max_tracks_per_artist,
            required_genres=tuple(required_genres or ()),
            released_before=released_before,
            released_after=released_after,
        ),
    )
    return {
        "feasible": outcome.feasible,
        "reason": outcome.reason.value if outcome.reason else None,
        "candidate_count": outcome.candidate_count,
        "max_achievable_ms": outcome.max_achievable_ms,
        "requested_min_ms": outcome.requested_min_ms,
    }
