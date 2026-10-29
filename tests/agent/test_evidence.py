import inspect
import json
from dataclasses import replace

from langchain_core.messages import AIMessage, ToolMessage

from deadwax.agent.evidence import HEADERS, evidence, rows
from deadwax.data import TRACKS
from deadwax.data.filters import FILTERS, select


def turn(name: str, args: dict, result: dict, call_id: str = "1") -> list:
    return [
        AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}]),
        ToolMessage(content=json.dumps(result), name=name, tool_call_id=call_id),
    ]


def test_filters_name_every_parameter_of_select():
    assert tuple(inspect.signature(select).parameters)[1:] == FILTERS


def test_no_tool_call_shows_the_whole_library():
    shown = evidence([AIMessage(content="hello")], TRACKS)
    assert shown.tracks == TRACKS
    assert shown.caption == "the whole library"


def test_a_search_shows_every_match_not_just_what_the_model_was_sent():
    messages = turn("query_library", {"genre": "jazz", "limit": 2}, {"total_matching": 9})
    shown = evidence(messages, TRACKS)
    assert len(shown.tracks) == len(select(TRACKS, genre="jazz"))
    assert len(shown.tracks) > 2
    assert shown.caption == "tracks tagged jazz"


def test_an_ordered_search_shows_the_same_top_tracks_the_tool_returned():
    args = {"order_by": "shortest", "limit": 1}
    shown = evidence(turn("query_library", args, {"total_matching": 100}), TRACKS)
    assert shown.tracks == (min(TRACKS, key=lambda t: t.duration_ms),)
    assert shown.caption == "the whole library, shortest first, top 1"


def test_an_ordered_search_without_a_limit_uses_the_tools_default():
    args = {"genre": "jazz", "order_by": "longest"}
    shown = evidence(turn("query_library", args, {"total_matching": 9}), TRACKS)
    durations = [t.duration_ms for t in shown.tracks]
    assert durations == sorted(durations, reverse=True)
    assert len(shown.tracks) == min(len(select(TRACKS, genre="jazz")), 20)


def test_the_last_search_is_the_one_shown():
    messages = [
        *turn("query_library", {"genre": "rap"}, {"total_matching": 0}, "1"),
        *turn("query_library", {"genre": "hip hop"}, {"total_matching": 9}, "2"),
    ]
    assert evidence(messages, TRACKS).caption == "tracks tagged hip hop"


def test_a_search_with_no_matches_shows_nothing():
    args = {"min_duration_ms": 600_000, "max_duration_ms": 120_000}
    shown = evidence(turn("query_library", args, {"total_matching": 0}), TRACKS)
    assert shown.tracks == ()
    assert shown.caption == "tracks at least 10:00 long, at most 2:00 long"


def test_a_validated_playlist_shows_its_tracks_in_order():
    ids = ["t003", "t001"]
    messages = turn("validate_playlist", {"track_ids": ids}, {"ok": True})
    shown = evidence(messages, TRACKS)
    assert [t.id for t in shown.tracks] == ids
    assert shown.caption == "the playlist in the answer"


def test_a_failed_playlist_says_so():
    messages = turn("validate_playlist", {"track_ids": ["t001"]}, {"ok": False})
    assert evidence(messages, TRACKS).caption == "the last playlist tried, which failed"


def test_an_impossible_request_shows_nothing():
    messages = turn("check_feasibility", {"required_genres": ["reggae"]}, {"feasible": False})
    shown = evidence(messages, TRACKS)
    assert shown.tracks == ()
    assert "cannot be met" in shown.caption


def test_artist_background_shows_that_artists_tracks():
    messages = turn("enrich_artist", {"artist": "Radiohead", "question": "who"}, {"passages": []})
    shown = evidence(messages, TRACKS)
    assert shown.tracks
    assert all("Radiohead" in t.artists for t in shown.tracks)


def test_a_row_has_a_cell_for_every_header():
    assert all(len(row) == len(HEADERS) for row in rows(TRACKS))


def test_a_missing_energy_or_play_date_is_left_blank():
    row = rows([replace(TRACKS[0], energy=None, last_played_at=None)])[0]
    assert row[5] == ""
    assert row[6] == ""
