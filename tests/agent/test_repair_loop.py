import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from deadwax.agent.repair_loop import MAX_REPAIR_ATTEMPTS, Stop, Verdict, inspect


def tool_message(name: str, payload: dict) -> ToolMessage:
    return ToolMessage(name=name, content=json.dumps(payload), tool_call_id=f"call-{name}")


def validated() -> ToolMessage:
    return tool_message("validate_playlist", {"ok": True, "track_count": 8, "violations": []})


def rejected() -> ToolMessage:
    return tool_message(
        "validate_playlist",
        {"ok": False, "violations": [{"code": "total_too_short", "adjust_by": 363000}]},
    )


def feasible(value: bool) -> ToolMessage:
    return tool_message("check_feasibility", {"feasible": value, "max_achievable_ms": 2400000})


def test_nothing_yet_is_not_a_stop():
    assert inspect([HumanMessage("build me a playlist")]) == Verdict()


def test_a_library_query_is_not_a_stop():
    messages = [tool_message("query_library", {"total_matching": 9, "tracks": []})]
    assert inspect(messages).stop is None


def test_a_passing_validation_stops_the_run():
    verdict = inspect([feasible(True), validated()])
    assert verdict.stop is Stop.VALIDATED
    assert verdict.detail["track_count"] == 8


def test_an_infeasible_brief_stops_before_generation():
    verdict = inspect([feasible(False)])
    assert verdict.stop is Stop.INFEASIBLE
    assert verdict.detail["max_achievable_ms"] == 2400000


@pytest.mark.parametrize("failures", range(1, MAX_REPAIR_ATTEMPTS + 1))
def test_repairs_within_the_budget_keep_going(failures):
    verdict = inspect([rejected()] * failures)
    assert verdict.stop is None
    assert verdict.failures == failures


def test_one_repair_past_the_budget_fails_honestly():
    verdict = inspect([rejected()] * (MAX_REPAIR_ATTEMPTS + 1))
    assert verdict.stop is Stop.UNREPAIRED
    assert verdict.failures == MAX_REPAIR_ATTEMPTS + 1


def test_a_repair_that_finally_passes_stops_on_the_pass():
    verdict = inspect([rejected(), rejected(), validated()])
    assert verdict.stop is Stop.VALIDATED
    assert verdict.failures == 2


def test_work_after_a_passing_validation_is_never_reached():
    messages = [validated(), AIMessage("let me check that again"), rejected()]
    assert inspect(messages).stop is Stop.VALIDATED


def test_a_tool_result_that_is_not_json_is_ignored():
    messages = [ToolMessage(name="query_library", content="9 tracks", tool_call_id="c1")]
    assert inspect(messages).stop is None
