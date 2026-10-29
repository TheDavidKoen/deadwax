from dataclasses import replace

import pytest

from runner import Case, Score, load_case, rate, score, scorecard

JAZZ = Case(
    name="counts-jazz-tracks",
    query="how many jazz tracks do I have?",
    expected_tool="query_library",
    expected_parameters={"genre": "jazz"},
    must_contain=("9",),
    must_contain_any=(),
    must_not_contain=("about",),
    must_cite=False,
)
SEARCH = [{"name": "query_library", "args": {"genre": "Jazz ", "limit": 5}}]


def test_a_correct_run_passes_every_dimension():
    result = score(JAZZ, SEARCH, "You have 9 jazz tracks.", converged=True)
    assert result == Score(tool=True, parameters=True, answer=True, converged=True)


def test_the_wrong_tool_fails_tool_and_parameters_but_not_the_answer():
    calls = [{"name": "check_feasibility", "args": {"required_genres": ["jazz"]}}]
    result = score(JAZZ, calls, "You have 9 jazz tracks.", converged=True)
    assert (result.tool, result.parameters, result.answer) == (False, False, True)


def test_parameters_must_appear_together_on_one_call():
    calls = [
        {"name": "query_library", "args": {"genre": "jazz"}},
        {"name": "query_library", "args": {"limit": 5}},
    ]
    case = replace(JAZZ, expected_parameters={"genre": "jazz", "limit": 5})
    assert score(case, calls, "9", converged=True).parameters is False


def test_a_forbidden_hedge_fails_the_answer():
    assert score(JAZZ, SEARCH, "You have about 9 jazz tracks.", True).answer is False


def test_matching_ignores_case():
    case = replace(JAZZ, must_contain=("Miles Davis",))
    assert score(case, SEARCH, "the longest is by MILES DAVIS", True).answer is True


def test_one_accepted_phrase_is_enough():
    case = replace(JAZZ, must_contain=(), must_contain_any=("cannot", "not possible"))
    assert score(case, SEARCH, "That is not possible.", True).answer is True
    assert score(case, SEARCH, "Here it is.", True).answer is False


def test_citing_a_passage_that_was_never_retrieved_fails_the_answer():
    case = replace(JAZZ, must_contain=())
    text = "Burial is William Bevan [burial-01]."
    assert score(case, SEARCH, text, True, retrieved=["burial-01"]).answer is True
    assert score(case, SEARCH, text, True, retrieved=["burial-02"]).answer is False


def test_a_case_that_must_cite_fails_without_a_citation():
    case = replace(JAZZ, must_contain=(), must_cite=True)
    assert (
        score(case, SEARCH, "Burial is William Bevan.", True, retrieved=["burial-01"]).answer
        is False
    )


def test_errored_attempts_are_left_out_of_a_rate():
    attempts = [{"error": None, "answer": True}, {"error": "503"}, {"error": None, "answer": False}]
    assert rate(attempts, "answer") == 0.5


def test_a_case_with_only_errors_has_no_rate():
    assert rate([{"error": "503"}], "answer") is None


def test_the_scorecard_counts_errors_per_case():
    results = [
        {
            "case": "counts-jazz-tracks",
            "attempts": [
                {
                    "error": None,
                    "tool": True,
                    "parameters": True,
                    "answer": True,
                    "converged": True,
                },
                {"error": "503"},
            ],
        }
    ]
    card = scorecard(results)
    assert card["per_case"][0]["errors"] == 1
    assert card["overall"]["answer"] == 1.0


def test_a_case_naming_a_tool_the_agent_lacks_is_rejected(tmp_path):
    path = tmp_path / "typo.toml"
    path.write_text('query = "q"\n[expect]\ntool = "query_libary"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="not a tool the agent has"):
        load_case(path)
