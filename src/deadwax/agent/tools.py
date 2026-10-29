from functools import cache

from langchain_core.tools import tool

from deadwax.agent.embeddings import embed_query
from deadwax.data import Track, library
from deadwax.data.filters import select
from deadwax.data.resolve import normalise
from deadwax.domain import Constraints, Violation, validator
from deadwax.retrieval.index import Index, read_index
from deadwax.retrieval.search import top_k

PASSAGES_RETURNED = 4
QUERY_LIMIT = 20
MIN_DURATION_WINDOW_MS = 120_000
DURATION_ADJUSTMENTS = ("DURATION_OVER", "DURATION_UNDER", "TRACK_TOO_LONG")

NO_ENERGY_ESTIMATE = "no estimate exists for this track"

ORDERINGS = {
    "longest": lambda t: -t.duration_ms,
    "shortest": lambda t: t.duration_ms,
    "highest_energy": lambda t: (t.energy is None, -t.energy.value if t.energy else 0.0),
    "lowest_energy": lambda t: (t.energy is None, t.energy.value if t.energy else 0.0),
}


def display_duration(duration_ms: int) -> str:
    minutes, seconds = divmod(duration_ms // 1000, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"


def _violation(violation: Violation) -> dict:
    payload = {
        "code": violation.code.value,
        "track_ids": list(violation.track_ids),
        "remedy": violation.remedy,
        "adjust_by": violation.adjust_by,
    }
    if violation.adjust_by is not None and violation.code in DURATION_ADJUSTMENTS:
        payload["adjust_by_display"] = display_duration(abs(violation.adjust_by))
    return payload


def _as_dict(track: Track) -> dict:
    return {
        "id": track.id,
        "name": track.name,
        "artists": list(track.artists),
        "duration_ms": track.duration_ms,
        "duration_display": display_duration(track.duration_ms),
        "genres": list(track.genres),
        "release_year": track.release_year,
        "energy": track.energy.value if track.energy else None,
        "energy_provenance": track.energy.provenance if track.energy else NO_ENERGY_ESTIMATE,
        "last_played_at": track.last_played_at.isoformat() if track.last_played_at else None,
    }


@cache
def _corpus() -> Index:
    return read_index()


@tool
def query_library(
    genre: str | None = None,
    artist: str | None = None,
    min_duration_ms: int | None = None,
    max_duration_ms: int | None = None,
    released_before: int | None = None,
    released_after: int | None = None,
    played: bool | None = None,
    order_by: str | None = None,
    limit: int = QUERY_LIMIT,
) -> dict:
    """Search the user's music library and return matching tracks with their totals.

    Call this before stating any fact about the library. Never estimate a count, a
    duration or a track name from your own knowledge, and never add numbers up
    yourself: use total_matching and total_duration_ms from the result, which are
    computed exactly. The tracks list is truncated to limit entries, so it may be
    shorter than total_matching.

    To find a longest, shortest, highest or lowest track, pass order_by as one of
    longest, shortest, highest_energy, lowest_energy and read the first entry. Never
    rank, compare or pick a maximum out of the list yourself; the ordering is computed
    here.

    Quote duration_display for a track and total_duration_display for a set of them.
    Never convert milliseconds to minutes yourself.

    Energy is an estimate, not a measurement. Every track carries energy_provenance
    saying where its value came from, and any answer that mentions energy must say it
    is an estimate.

    If a genre search finds nothing, known_genres lists the genre tags the library
    actually uses. If the user's word is another name for one of them, as rap is for
    hip hop, search again with that tag and say which tag you searched. Never
    substitute a genre that is merely related.
    """
    if order_by is not None and order_by not in ORDERINGS:
        return {"invalid_order_by": order_by, "allowed": sorted(ORDERINGS)}

    matches = select(
        library.tracks(),
        genre=genre,
        artist=artist,
        min_duration_ms=min_duration_ms,
        max_duration_ms=max_duration_ms,
        released_before=released_before,
        released_after=released_after,
        played=played,
    )
    if order_by is not None:
        matches = sorted(matches, key=ORDERINGS[order_by])

    total_ms = sum(t.duration_ms for t in matches)
    result = {
        "total_matching": len(matches),
        "total_duration_ms": total_ms,
        "total_duration_display": display_duration(total_ms),
        "tracks": [_as_dict(t) for t in matches[:limit]],
    }
    if genre is not None and not matches:
        result["known_genres"] = sorted({g for t in library.tracks() for g in t.genres})
    if played is not None and (history := library.play_history()):
        result["play_history"] = history
    return result


@tool
def validate_playlist(
    track_ids: list[str],
    min_total_duration_ms: int | None = None,
    max_total_duration_ms: int | None = None,
    max_track_duration_ms: int | None = None,
    max_tracks_per_artist: int | None = None,
    required_genres: list[str] | None = None,
    released_before: int | None = None,
    released_after: int | None = None,
    target_energy: float | None = None,
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

    A duration violation also carries adjust_by_display, the same amount written in
    minutes and seconds. Show the user that, never the millisecond figure.

    Pass the same release-year bounds you gave check_feasibility, so a track outside
    the window is caught here too.

    If the user asks for an energy level or a mood, pass target_energy between 0 and 1.
    It is scored, never enforced: soft_scores reports how close the playlist came, and
    because energy is estimated rather than measured, any answer that mentions it must
    say so.
    """
    by_id = {t.id: t for t in library.tracks()}
    unknown = [i for i in track_ids if i not in by_id]
    if unknown:
        return {"ok": False, "unknown_track_ids": unknown}

    bounds = (
        min_total_duration_ms,
        max_total_duration_ms,
        max_track_duration_ms,
        max_tracks_per_artist,
        released_before,
        released_after,
    )
    if all(bound is None for bound in bounds) and not required_genres:
        return {
            "ok": False,
            "invalid_constraints": "no constraints were supplied, so there is nothing to check",
            "remedy": (
                "an unconstrained playlist cannot be validated: ask the user how long it "
                "should be, what genre, or how many tracks per artist, before proposing one"
            ),
        }

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
            released_before=released_before,
            released_after=released_after,
            target_energy=target_energy,
        ),
    )
    total_ms = sum(by_id[i].duration_ms for i in track_ids)
    return {
        "ok": result.ok,
        "total_duration_ms": total_ms,
        "total_duration_display": display_duration(total_ms),
        "track_count": len(track_ids),
        "violations": [_violation(v) for v in result.violations],
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

    max_achievable_display is the longest playlist the library can produce under these
    constraints. When explaining a refusal, describe what the user asked for in their
    own words and quote max_achievable_display for what is possible. Never show the
    user a millisecond figure and never convert one yourself.

    A brief with no constraints at all cannot be checked. If the user has not said how
    long the playlist should be or what should be in it, ask them before calling this.
    """
    bounds = (
        min_total_duration_ms,
        max_track_duration_ms,
        max_tracks_per_artist,
        released_before,
        released_after,
    )
    if all(bound is None for bound in bounds) and not required_genres:
        return {
            "needs_clarification": True,
            "reason": "no_constraints_given",
            "remedy": (
                "the brief is empty: ask the user how long the playlist should be, what "
                "genre, or which artists, before checking anything"
            ),
        }

    outcome = validator.check_feasibility(
        library.tracks(),
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
        "max_achievable_display": display_duration(outcome.max_achievable_ms),
        "requested_min_ms": outcome.requested_min_ms,
    }


@tool
def enrich_artist(artist: str, question: str) -> dict:
    """Look up background on one artist in the user's library, from published sources.

    Call this for any question about an artist's history, members, origins, influences
    or career. Pass the artist's name and the user's question. It returns the passages
    from MusicBrainz and Wikipedia that best match the question.

    Answer only from these passages. If they do not contain the answer, tell the user
    your sources do not cover it, even if you believe you know. Never fill the gap from
    your own knowledge.

    Cite every passage you use by its id in square brackets, such as [can-03], straight
    after the claim it supports. Never cite an id this tool did not return.

    This tool knows nothing about the user's tracks. Use query_library for those.
    """
    index = _corpus()
    wanted = normalise(artist)
    positions = [p for p, chunk in enumerate(index.chunks) if normalise(chunk.artist) == wanted]
    if not positions:
        return {
            "unknown_artist": artist,
            "known_artists": sorted({chunk.artist for chunk in index.chunks}),
            "remedy": (
                "there is no background on artists outside the user's library: say so, "
                "or retry with one of known_artists if the user meant one of them"
            ),
        }

    hits = top_k(embed_query(question), [index.vectors[p] for p in positions], PASSAGES_RETURNED)
    chunks = [index.chunks[positions[hit.position]] for hit in hits]
    return {
        "artist": chunks[0].artist,
        "passages": [
            {
                "id": chunk.id,
                "section": chunk.section,
                "text": chunk.text,
                "source": chunk.source,
                "licence": chunk.licence,
            }
            for chunk in chunks
        ],
    }


TOOLS = (check_feasibility, query_library, validate_playlist, enrich_artist)
