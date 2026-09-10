import argparse
import json
import logging
import os
import sys
import tomllib
import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from deadwax.agent import answer_text, ask
from deadwax.agent.tools import check_feasibility, query_library, validate_playlist
from deadwax.config import load_env_file

CASES_DIR = Path("evals") / "cases"
RESULTS_DIR = Path("evals") / "results"
TOOL_NAMES = {tool.name for tool in (check_feasibility, query_library, validate_playlist)}

warnings.filterwarnings("ignore", message="Model .* uses fixed sampling defaults")
logging.getLogger("google_genai").setLevel(logging.ERROR)


@dataclass(frozen=True)
class Case:
    name: str
    query: str
    expected_tool: str | None
    expected_parameters: dict
    must_contain: tuple[str, ...]
    must_contain_any: tuple[str, ...]
    must_not_contain: tuple[str, ...]


@dataclass(frozen=True)
class Score:
    tool: bool
    parameters: bool
    answer: bool
    converged: bool


def load_case(path: Path) -> Case:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    expect = raw.get("expect", {})
    answer = expect.get("answer", {})

    if "query" not in raw:
        raise ValueError(f"{path.name}: missing required key 'query'")

    expected_tool = expect.get("tool")
    if expected_tool is not None and expected_tool not in TOOL_NAMES:
        raise ValueError(
            f"{path.name}: expect.tool is '{expected_tool}', "
            f"which is not a tool the agent has. Known tools: {sorted(TOOL_NAMES)}"
        )

    return Case(
        name=path.stem,
        query=raw["query"],
        expected_tool=expected_tool,
        expected_parameters=expect.get("parameters", {}),
        must_contain=tuple(answer.get("must_contain", ())),
        must_contain_any=tuple(answer.get("must_contain_any", ())),
        must_not_contain=tuple(answer.get("must_not_contain", ())),
    )


def load_cases(directory: Path) -> list[Case]:
    paths = sorted(directory.glob("*.toml"))
    if not paths:
        raise ValueError(f"no case files found in {directory}")
    return [load_case(path) for path in paths]


def argument_matches(actual: object, expected: object) -> bool:
    if isinstance(actual, str) and isinstance(expected, str):
        return actual.strip().lower() == expected.strip().lower()
    return actual == expected


def score(case: Case, calls: Sequence[dict], text: str, converged: bool) -> Score:
    matching = [call for call in calls if call["name"] == case.expected_tool]
    tool_ok = case.expected_tool is None or bool(matching)

    if not case.expected_parameters:
        parameters_ok = True
    else:
        parameters_ok = any(
            all(
                argument_matches(call["args"].get(key), value)
                for key, value in case.expected_parameters.items()
            )
            for call in matching
        )

    lowered = text.lower()
    answer_ok = (
        all(fact.lower() in lowered for fact in case.must_contain)
        and (not case.must_contain_any or any(f.lower() in lowered for f in case.must_contain_any))
        and not any(fact.lower() in lowered for fact in case.must_not_contain)
    )

    return Score(tool=tool_ok, parameters=parameters_ok, answer=answer_ok, converged=converged)


def run_case(case: Case, repeats: int, model: str) -> list[dict]:
    attempts = []
    for attempt in range(1, repeats + 1):
        print(f"  {case.name} [{attempt}/{repeats}] ... ", end="", flush=True, file=sys.stderr)
        try:
            answer = ask(case.query, model_name=model)
        except Exception as error:
            print(f"ERROR {type(error).__name__}", file=sys.stderr)
            attempts.append({"attempt": attempt, "error": f"{type(error).__name__}: {error}"})
            continue

        if answer.error is not None:
            print(f"ERROR {answer.error.partition(':')[0]}", file=sys.stderr)
            attempts.append({"attempt": attempt, "error": answer.error})
            continue

        calls = answer.tool_calls()
        text = answer_text(answer.messages[-1]) if answer.messages else ""
        result = score(case, calls, text, answer.converged)
        print(
            f"tool={'y' if result.tool else 'n'} "
            f"params={'y' if result.parameters else 'n'} "
            f"answer={'y' if result.answer else 'n'}",
            file=sys.stderr,
        )
        attempts.append(
            {
                "attempt": attempt,
                "error": None,
                "converged": result.converged,
                "stop": answer.stop,
                "tool": result.tool,
                "parameters": result.parameters,
                "answer": result.answer,
                "tool_calls": calls,
                "final_text": text,
                "total_tokens": answer.total_tokens(),
            }
        )
    return attempts


def rate(attempts: Sequence[dict], dimension: str) -> float | None:
    scored = [a for a in attempts if a.get("error") is None]
    if not scored:
        return None
    return round(sum(1 for a in scored if a[dimension]) / len(scored), 3)


def scorecard(results: Sequence[dict]) -> dict:
    dimensions = ("tool", "parameters", "answer", "converged")
    per_case = [
        {
            "case": r["case"],
            "attempts": len(r["attempts"]),
            "errors": sum(1 for a in r["attempts"] if a.get("error") is not None),
            **{d: rate(r["attempts"], d) for d in dimensions},
        }
        for r in results
    ]
    every_attempt = [a for r in results for a in r["attempts"]]
    return {
        "cases": len(results),
        "overall": {d: rate(every_attempt, d) for d in dimensions},
        "per_case": per_case,
    }


def cell(value: float | None) -> str:
    return "    --" if value is None else f"{value:>6.0%}"


def print_scorecard(card: dict) -> None:
    header = f"{'case':<34}{'tool':>8}{'params':>8}{'answer':>8}{'conv':>8}{'err':>6}"
    print(header)
    print("-" * len(header))

    for row in card["per_case"]:
        print(
            f"{row['case']:<34}{cell(row['tool'])}{cell(row['parameters'])}"
            f"{cell(row['answer'])}{cell(row['converged'])}{row['errors']:>6}"
        )

    overall = card["overall"]
    print("-" * len(header))
    print(
        f"{'OVERALL':<34}{cell(overall['tool'])}{cell(overall['parameters'])}"
        f"{cell(overall['answer'])}{cell(overall['converged'])}"
    )


def rescore(path: Path, cases: dict[str, Case]) -> None:
    recorded = json.loads(path.read_text(encoding="utf-8"))

    for result in recorded["results"]:
        case = cases.get(result["case"])
        if case is None:
            print(f"  skipped {result['case']}: no matching case file", file=sys.stderr)
            continue
        for attempt in result["attempts"]:
            if attempt.get("error") is not None:
                continue
            fresh = score(case, attempt["tool_calls"], attempt["final_text"], attempt["converged"])
            attempt["tool"] = fresh.tool
            attempt["parameters"] = fresh.parameters
            attempt["answer"] = fresh.answer

    recorded["scorecard"] = scorecard(recorded["results"])
    recorded["rescored_at"] = datetime.now(UTC).isoformat()
    path.write_text(json.dumps(recorded, indent=2), encoding="utf-8")

    print_scorecard(recorded["scorecard"])
    print()
    print(f"rescored in place: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="evals",
        description=(
            "Run every hand-written case in evals/cases/ and report pass rates for tool "
            "selection, parameter extraction and answer content, scored separately."
        ),
    )
    parser.add_argument(
        "--fixtures-only",
        action="store_true",
        help="validate the case files without calling a model; used by CI, needs no API key",
    )
    parser.add_argument("--repeats", type=int, default=3, help="runs per case")
    parser.add_argument(
        "--model",
        default="gemini-3.5-flash-lite",
        help="the model to pin; a sample spread across models measures the models",
    )
    parser.add_argument("--rpm", type=int, default=12, help="client-side request ceiling")
    parser.add_argument("--case", help="run a single case by name")
    parser.add_argument(
        "--rescore",
        help=(
            "re-grade a recorded results file against the current cases, without calling a "
            "model. Use after correcting an answer key."
        ),
    )
    args = parser.parse_args()

    try:
        cases = load_cases(CASES_DIR)
    except ValueError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error

    if args.case:
        cases = [c for c in cases if c.name == args.case]
        if not cases:
            print(f"no case named '{args.case}'", file=sys.stderr)
            raise SystemExit(1)

    if args.fixtures_only:
        print(f"{len(cases)} case(s) loaded and valid")
        for case in cases:
            print(f"  {case.name}")
        return

    if args.rescore:
        rescore(Path(args.rescore), {case.name: case for case in cases})
        return

    os.environ.setdefault("DEADWAX_RPM", str(args.rpm))
    load_env_file()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = RESULTS_DIR / f"{args.model}-{stamp}.json"

    results: list[dict] = []
    for case in cases:
        results.append({"case": case.name, "query": case.query, "attempts": []})
        results[-1]["attempts"] = run_case(case, args.repeats, args.model)
        path.write_text(
            json.dumps(
                {
                    "model": args.model,
                    "repeats": args.repeats,
                    "recorded_at": datetime.now(UTC).isoformat(),
                    "scorecard": scorecard(results),
                    "results": results,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    print()
    print_scorecard(scorecard(results))
    print()
    print(f"written to {path}")


if __name__ == "__main__":
    main()
