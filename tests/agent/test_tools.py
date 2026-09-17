import json

import pytest
from langchain_core.messages import ToolMessage

from deadwax.agent.repair_loop import Stop, inspect
from deadwax.agent.tools import ORDERINGS, _display, check_feasibility, query_library
from deadwax.agent.tools import validate_playlist as validate
from deadwax.data import TRACKS

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
