import argparse
import sys

from deadwax.agent import answer_text, ask, tracing, transcript
from deadwax.config import load_env_file, use_utf8_output
from deadwax.data import library
from deadwax.retrieval.citations import cited, source_lines, unretrieved


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="deadwax",
        description=(
            "Ask the music librarian a question. It reads the fixture library unless "
            "DEADWAX_LIBRARY names a database built by deadwax-spotify."
        ),
    )
    parser.add_argument("question", nargs="+", help="the question to ask")
    parser.add_argument(
        "--model",
        help="pin a single model instead of falling back through the free-tier list",
    )
    args = parser.parse_args()

    use_utf8_output()
    load_env_file()
    try:
        library.tracks()
    except FileNotFoundError as error:
        raise SystemExit(str(error)) from error
    answer = ask(" ".join(args.question), model_name=args.model)

    for name in answer.exhausted:
        print(f"[skipped] {name} is rate limited", file=sys.stderr)
    print(f"[model] {answer.model}", file=sys.stderr)
    print(f"[library] {library.source()}", file=sys.stderr)

    for call in answer.tool_calls():
        print(f"[tool] {call['name']}({call['args']})", file=sys.stderr)

    if not answer.converged:
        print(f"[warning] did not converge: {answer.error}", file=sys.stderr)

    if answer.trace_url:
        print(f"[trace] {answer.trace_url}", file=sys.stderr)

    text = answer_text(answer.messages[-1]) if answer.messages else ""
    print(text)

    passages = transcript.retrieved_passages(answer.messages)
    citations = cited(text)
    for chunk_id in unretrieved(citations, passages):
        print(f"[warning] cited a passage it was never given: {chunk_id}", file=sys.stderr)
    lines = source_lines(citations, passages)
    if lines:
        print("\nSources")
        print("\n".join(lines))
    tracing.flush()


if __name__ == "__main__":
    main()
