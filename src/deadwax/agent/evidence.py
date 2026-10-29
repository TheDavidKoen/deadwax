from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from deadwax.agent import transcript
from deadwax.agent.tools import ORDERINGS, QUERY_LIMIT, display_duration
from deadwax.data import Track
from deadwax.data.filters import FILTERS, select

HEADERS = ("Track", "Artists", "Length", "Genres", "Year", "Energy (estimate)", "Last played")


@dataclass(frozen=True)
class Evidence:
    tracks: tuple[Track, ...]
    caption: str


def _described(filters: dict[str, Any]) -> str:
    phrases = {
        "genre": lambda v: f"tagged {v}",
        "artist": lambda v: f"by {v}",
        "min_duration_ms": lambda v: f"at least {display_duration(int(v))} long",
        "max_duration_ms": lambda v: f"at most {display_duration(int(v))} long",
        "released_before": lambda v: f"released before {v}",
        "released_after": lambda v: f"released after {v}",
        "played": lambda v: "played" if v else "never played",
    }
    parts = [phrases[name](value) for name, value in filters.items()]
    return "tracks " + ", ".join(parts) if parts else "the whole library"


def _last(calls: list[dict], name: str) -> dict | None:
    return next((call for call in reversed(calls) if call["name"] == name), None)


def evidence(messages: Sequence[Any], tracks: Sequence[Track]) -> Evidence:
    calls = transcript.tool_calls(messages)
    results = transcript.tool_results(messages)

    if playlist := _last(calls, "validate_playlist"):
        by_id = {t.id: t for t in tracks}
        chosen = tuple(by_id[i] for i in playlist["args"].get("track_ids", []) if i in by_id)
        verdicts = [payload for name, payload in results if name == "validate_playlist"]
        passed = bool(verdicts) and verdicts[-1].get("ok") is True
        caption = (
            "the playlist in the answer" if passed else "the last playlist tried, which failed"
        )
        return Evidence(chosen, caption)

    if search := _last(calls, "query_library"):
        args = search["args"]
        filters = {
            name: value for name, value in args.items() if name in FILTERS and value is not None
        }
        matches = select(tracks, **filters)
        caption = _described(filters)
        if (order_by := args.get("order_by")) in ORDERINGS:
            limit = int(args.get("limit", QUERY_LIMIT))
            matches = sorted(matches, key=ORDERINGS[order_by])[:limit]
            caption = f"{caption}, {order_by.replace('_', ' ')} first, top {len(matches)}"
        return Evidence(tuple(matches), caption)

    feasibility = [payload for name, payload in results if name == "check_feasibility"]
    if feasibility and feasibility[-1].get("feasible") is False:
        return Evidence((), "no tracks: the request cannot be met from this library")

    if background := _last(calls, "enrich_artist"):
        artist = background["args"].get("artist", "")
        return Evidence(tuple(select(tracks, artist=artist)), f"tracks by {artist}")

    return Evidence(tuple(tracks), "the whole library")


def rows(tracks: Sequence[Track]) -> list[list[str]]:
    return [
        [
            t.name,
            ", ".join(t.artists),
            display_duration(t.duration_ms),
            ", ".join(t.genres),
            str(t.release_year),
            f"{t.energy.value:.2f}" if t.energy else "",
            t.last_played_at.isoformat() if t.last_played_at else "",
        ]
        for t in tracks
    ]
