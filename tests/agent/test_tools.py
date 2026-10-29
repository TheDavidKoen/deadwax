import json
from dataclasses import replace

import pytest
from langchain_core.messages import ToolMessage

from deadwax.agent import tools, transcript
from deadwax.agent.repair_loop import Stop, inspect
from deadwax.agent.tools import ORDERINGS, _display, check_feasibility, enrich_artist, query_library
from deadwax.agent.tools import validate_playlist as validate
from deadwax.data import TRACKS, library
from deadwax.retrieval.chunking import Chunk
from deadwax.retrieval.index import Index

ORDER_CASES = [
    ("longest", "duration_ms", True),
    ("shortest", "duration_ms", False),
    ("highest_energy", "energy", True),
    ("lowest_energy", "energy", False),
]


def search(**kwargs) -> dict:
    return query_library.invoke(kwargs)


def test_a_track_carries_its_energy_and_where_the_value_came_from():
    track = search(artist="Radiohead")["tracks"][0]
    assert 0.0 <= track["energy"] <= 1.0
    assert track["energy_provenance"]


def test_a_set_of_tracks_carries_a_readable_total():
    result = search(genre="jazz")
    assert result["total_duration_display"] == _display(result["total_duration_ms"])


@pytest.mark.parametrize(("order_by", "field", "descending"), ORDER_CASES)
def test_an_ordering_is_applied_before_the_result_is_truncated(order_by, field, descending):
    values = [t[field] for t in search(order_by=order_by, limit=len(TRACKS))["tracks"]]
    assert values == sorted(values, reverse=descending)


def test_ordering_by_longest_puts_the_longest_track_first():
    assert search(order_by="longest")["tracks"][0]["name"] == "Coffin for Head of State"


def test_every_ordering_is_covered_by_a_case():
    assert set(ORDERINGS) == {order_by for order_by, _, _ in ORDER_CASES}


def test_an_unknown_ordering_is_reported_rather_than_raised():
    result = search(order_by="loudest")
    assert result["invalid_order_by"] == "loudest"
    assert "longest" in result["allowed"]


def test_a_total_over_an_hour_displays_hours():
    assert _display(6_085_000) == "1:41:25"
    assert _display(251_000) == "4:11"


def as_tool_message(name: str, payload: dict) -> ToolMessage:
    return ToolMessage(name=name, content=json.dumps(payload), tool_call_id=f"call-{name}")


def test_an_unconstrained_playlist_cannot_be_validated():
    result = validate.invoke({"track_ids": ["t001", "t002"]})
    assert result["ok"] is False
    assert "ask the user" in result["remedy"]


def test_an_empty_brief_asks_for_clarification_rather_than_refusing():
    result = check_feasibility.invoke({})
    assert result["needs_clarification"] is True
    assert "feasible" not in result


def test_an_empty_brief_does_not_end_the_run_as_infeasible():
    message = as_tool_message("check_feasibility", check_feasibility.invoke({}))
    assert inspect([message]).stop is None


def test_a_genuinely_infeasible_brief_still_ends_the_run():
    payload = check_feasibility.invoke(
        {
            "required_genres": ["jazz"],
            "min_total_duration_ms": 3_600_000,
            "max_track_duration_ms": 360_000,
        }
    )
    assert inspect([as_tool_message("check_feasibility", payload)]).stop is Stop.INFEASIBLE


def test_a_duration_violation_carries_a_readable_adjustment():
    result = validate.invoke({"track_ids": ["t001"], "min_total_duration_ms": 1_800_000})
    violation = next(v for v in result["violations"] if v["code"] == "DURATION_UNDER")
    assert violation["adjust_by"] == 1_549_000
    assert violation["adjust_by_display"] == "25:49"


def test_a_count_violation_carries_no_duration_display():
    result = validate.invoke({"track_ids": ["t001", "t003", "t004"], "max_tracks_per_artist": 2})
    violation = next(v for v in result["violations"] if v["code"] == "ARTIST_LIMIT_EXCEEDED")
    assert "adjust_by_display" not in violation


def test_a_track_length_violation_carries_a_readable_adjustment():
    result = validate.invoke({"track_ids": ["t002"], "max_track_duration_ms": 300_000})
    violation = next(v for v in result["violations"] if v["code"] == "TRACK_TOO_LONG")
    assert violation["adjust_by_display"] == _display(abs(violation["adjust_by"]))


def test_an_infeasible_brief_reports_its_limit_readably():
    result = check_feasibility.invoke(
        {"required_genres": ["hip hop"], "min_total_duration_ms": 1_800_000}
    )
    assert result["feasible"] is False
    assert result["max_achievable_display"] == _display(result["max_achievable_ms"])


def test_a_target_energy_is_scored_with_its_provenance():
    result = validate.invoke(
        {"track_ids": ["t001"], "max_track_duration_ms": 600_000, "target_energy": 0.4}
    )
    assert result["ok"] is True
    [score] = result["soft_scores"]
    assert score["name"] == "energy"
    assert "estimate" in score["provenance"]


def test_a_target_energy_alone_is_not_a_brief():
    result = validate.invoke({"track_ids": ["t001"], "target_energy": 0.8})
    assert result["ok"] is False
    assert "invalid_constraints" in result


def test_a_release_year_window_is_enforced_on_validation():
    result = validate.invoke({"track_ids": ["t001"], "released_before": 2000})
    codes = [v["code"] for v in result["violations"]]
    assert codes == ["RELEASE_YEAR_OUT_OF_RANGE"]


def test_a_genre_search_that_finds_nothing_offers_the_library_vocabulary():
    result = search(genre="rap")
    assert result["total_matching"] == 0
    assert "hip hop" in result["known_genres"]


def test_a_genre_search_that_finds_tracks_does_not_offer_the_vocabulary():
    assert "known_genres" not in search(genre="hip hop")


def passage(chunk_id: str, artist: str) -> Chunk:
    return Chunk(
        id=chunk_id,
        artist=artist,
        section="Introduction",
        text=f"{artist} — Introduction\ntext of {chunk_id}",
        source=f"https://en.wikipedia.org/wiki/{artist}",
        licence="CC BY-SA 4.0",
    )


FAKE_CORPUS = Index(
    model="fake",
    dimensions=2,
    built="2026-10-28",
    chunks=(
        passage("can-01", "Can"),
        passage("can-02", "Can"),
        passage("bjork-01", "Bjork"),
    ),
    vectors=((0.0, 1.0), (1.0, 0.0), (1.0, 0.0)),
)


@pytest.fixture
def queries(monkeypatch) -> list[str]:
    sent: list[str] = []

    def fake_embed_query(text: str) -> list[float]:
        sent.append(text)
        return [1.0, 0.0]

    monkeypatch.setattr(tools, "_corpus", lambda: FAKE_CORPUS)
    monkeypatch.setattr(tools, "embed_query", fake_embed_query)
    return sent


def enrich(**kwargs) -> dict:
    return enrich_artist.invoke(kwargs)


def test_only_the_named_artists_passages_are_returned(queries):
    result = enrich(artist="Can", question="who founded them")
    assert {p["id"] for p in result["passages"]} == {"can-01", "can-02"}


def test_passages_are_ranked_by_how_well_they_match_the_question(queries):
    result = enrich(artist="Can", question="who founded them")
    assert [p["id"] for p in result["passages"]] == ["can-02", "can-01"]


def test_no_more_than_the_passage_limit_is_returned(queries, monkeypatch):
    monkeypatch.setattr(tools, "PASSAGES_RETURNED", 1)
    assert len(enrich(artist="Can", question="anything")["passages"]) == 1


def test_an_artist_is_found_whatever_the_case_or_accents(queries):
    assert enrich(artist="BJÖRK", question="where is she from")["artist"] == "Bjork"


def test_every_passage_carries_its_source_and_licence(queries):
    for p in enrich(artist="Can", question="anything")["passages"]:
        assert p["source"].startswith("https://")
        assert p["licence"]


def test_the_question_is_what_gets_embedded(queries):
    enrich(artist="Can", question="when did they split up")
    assert queries == ["when did they split up"]


def test_an_artist_outside_the_library_is_refused_without_a_model_call(queries):
    result = enrich(artist="Oasis", question="who is in the band")
    assert result["unknown_artist"] == "Oasis"
    assert result["known_artists"] == ["Bjork", "Can"]
    assert queries == []


def test_retrieved_passages_are_collected_from_the_transcript(queries):
    result = enrich(artist="Can", question="anything")
    message = ToolMessage(json.dumps(result), name="enrich_artist", tool_call_id="1")
    passages = transcript.retrieved_passages([message])
    assert sorted(passages) == ["can-01", "can-02"]
    assert passages["can-01"]["artist"] == "Can"


def test_a_track_with_no_energy_estimate_says_so(monkeypatch):
    unknown = replace(TRACKS[0], energy=None)
    monkeypatch.setattr(library, "tracks", lambda: (unknown,))
    track = search()["tracks"][0]
    assert track["energy"] is None
    assert track["energy_provenance"] == tools.NO_ENERGY_ESTIMATE


def test_never_played_tracks_are_counted_here_not_by_the_model():
    never = sum(t.last_played_at is None for t in TRACKS)
    assert search(played=False, limit=0)["total_matching"] == never
    assert search(played=True, limit=0)["total_matching"] == len(TRACKS) - never


def test_the_played_filter_combines_with_the_others():
    result = search(genre="jazz", played=False, limit=len(TRACKS))
    assert all(t["last_played_at"] is None for t in result["tracks"])
    assert all("jazz" in t["genres"] for t in result["tracks"])


def test_complete_play_history_carries_no_warning(monkeypatch):
    monkeypatch.setenv(library.LIBRARY_VARIABLE, library.FIXTURES)
    assert "play_history" not in search(played=False)


def test_partial_play_history_is_disclosed(monkeypatch):
    monkeypatch.setenv(library.LIBRARY_VARIABLE, "data/library.sqlite")
    monkeypatch.setattr(library, "tracks", lambda: TRACKS)
    assert search(played=False)["play_history"] == library.PARTIAL_PLAY_HISTORY


def test_play_history_is_not_mentioned_unless_asked_about(monkeypatch):
    monkeypatch.setenv(library.LIBRARY_VARIABLE, "data/library.sqlite")
    monkeypatch.setattr(library, "tracks", lambda: TRACKS)
    assert "play_history" not in search(genre="jazz")


@pytest.mark.parametrize("order_by", ["highest_energy", "lowest_energy"])
def test_tracks_with_no_energy_estimate_sort_last(monkeypatch, order_by):
    unknown = replace(TRACKS[0], id="unknown", energy=None)
    monkeypatch.setattr(library, "tracks", lambda: (unknown, *TRACKS[1:4]))
    assert search(order_by=order_by)["tracks"][-1]["id"] == "unknown"
