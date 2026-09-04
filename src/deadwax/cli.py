import argparse
import sys

from deadwax.agent.loop import ask
from deadwax.agent.transcript import answer_text
from deadwax.config import load_env_file


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="deadwax",
        description="Ask the music librarian a question about the fixture library.",
    )
    parser.add_argument("question", nargs="+", help="the question to ask")
    parser.add_argument(
        "--model",
        help="pin a single model instead of falling back through the free-tier list",
    )
    args = parser.parse_args()

    load_env_file()
    answer = ask(" ".join(args.question), model_name=args.model)

    for name in answer.exhausted:
        print(f"[skipped] {name} is rate limited", file=sys.stderr)
    print(f"[model] {answer.model}", file=sys.stderr)

    for call in answer.tool_calls():
        print(f"[tool] {call['name']}({call['args']})", file=sys.stderr)

    if not answer.converged:
        print(f"[warning] did not converge: {answer.error}", file=sys.stderr)

    print(answer_text(answer.messages[-1]) if answer.messages else "")


if __name__ == "__main__":
    main()
