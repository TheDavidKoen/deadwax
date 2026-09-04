import argparse
import json
import os
import sys
import time
import warnings
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from deadwax.agent import Answer, answer_text, ask
from deadwax.config import load_env_file

OUT_DIR = Path("evals") / "variance"

warnings.filterwarnings("ignore", message=".*fixed sampling defaults.*")


def selected_track_ids(calls: list[dict]) -> list[str]:
    for call in reversed(calls):
        if call["name"] == "validate_playlist":
            return sorted(call["args"].get("track_ids", []))
    return []


def summarise(results: list[dict]) -> dict:
    observed = [r for r in results if r.get("tool_calls")]
    converged = [r for r in observed if r.get("converged")]
    sequences = Counter(tuple(c["name"] for c in r["tool_calls"]) for r in observed)
    selections = Counter(tuple(selected_track_ids(r["tool_calls"])) for r in observed)
    answers = Counter(r["final_text"] for r in converged)
    call_counts = [len(r["tool_calls"]) for r in observed]
    tokens = [r["total_tokens"] for r in observed if r["total_tokens"]]

    return {
        "observed": len(observed),
        "converged": len(converged),
        "did_not_converge": len(observed) - len(converged),
        "no_data": len(results) - len(observed),
        "distinct_tool_sequences": len(sequences),
        "tool_sequences": [
            {"sequence": list(seq), "count": n} for seq, n in sequences.most_common()
        ],
        "tool_call_count_range": [min(call_counts), max(call_counts)] if call_counts else [],
        "distinct_track_selections": len(selections),
        "track_selections": [
            {"track_ids": list(sel), "count": n} for sel, n in selections.most_common()
        ],
        "distinct_answers": len(answers),
        "token_range": [min(tokens), max(tokens)] if tokens else [],
        "token_mean": round(sum(tokens) / len(tokens)) if tokens else None,
    }


def record_of(query: str, model: str, runs: int, results: list[dict]) -> dict:
    return {
        "query": query,
        "model": model,
        "runs": runs,
        "recorded_at": datetime.now(UTC).isoformat(),
        "summary": summarise(results),
        "results": results,
    }


def result_of(index: int, answer: Answer, elapsed_ms: int) -> dict:
    calls = answer.tool_calls()
    return {
        "run": index,
        "error": answer.error,
        "converged": answer.converged,
        "model": answer.model,
        "elapsed_ms": elapsed_ms,
        "requests": len(calls) + 1,
        "tool_calls": calls,
        "total_tokens": answer.total_tokens(),
        "final_text": answer_text(answer.messages[-1]) if answer.messages else "",
    }


def run(query: str, runs: int, model: str, path: Path) -> dict:
    results: list[dict] = []

    for index in range(1, runs + 1):
        print(f"run {index}/{runs} ... ", end="", flush=True, file=sys.stderr)
        started = time.perf_counter()

        try:
            answer = ask(query, model_name=model)
        except Exception as error:
            print(f"FAILED {type(error).__name__}: {error}", file=sys.stderr)
            results.append({"run": index, "error": f"{type(error).__name__}: {error}"})
        else:
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            results.append(result_of(index, answer, elapsed_ms))
            outcome = "converged" if answer.converged else f"DID NOT CONVERGE ({answer.error})"
            print(f"{len(answer.tool_calls())} calls, {outcome}", file=sys.stderr)

        path.write_text(
            json.dumps(record_of(query, model, runs, results), indent=2), encoding="utf-8"
        )

    return record_of(query, model, runs, results)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="measure-variance",
        description=(
            "Run one query repeatedly against a pinned model and report what varied "
            "between runs. Writes every tool call and answer to evals/variance/."
        ),
    )
    parser.add_argument("query", nargs="+", help="the query to repeat")
    parser.add_argument("--runs", type=int, default=10, help="how many times to run it")
    parser.add_argument(
        "--model",
        default="gemini-3.5-flash-lite",
        help="the model to pin; comparability requires one model for the whole sample",
    )
    parser.add_argument(
        "--rpm",
        type=int,
        default=12,
        help="client-side request ceiling, kept below the provider's per-minute limit",
    )
    args = parser.parse_args()

    os.environ.setdefault("DEADWAX_RPM", str(args.rpm))
    load_env_file()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{args.model}-{stamp}.json"

    record = run(" ".join(args.query), args.runs, args.model, path)

    print()
    print(json.dumps(record["summary"], indent=2))
    print()
    print(f"written to {path}")


if __name__ == "__main__":
    main()
