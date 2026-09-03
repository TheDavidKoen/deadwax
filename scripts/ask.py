import sys
from pathlib import Path

from deadwax.agent.loop import ask
from raw_call import load_env_file


def text_of(message) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    return "".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )


def main() -> None:
    load_env_file(Path(__file__).resolve().parent.parent / ".env")

    args = sys.argv[1:]
    pinned = None
    if "--model" in args:
        index = args.index("--model")
        pinned = args[index + 1] if index + 1 < len(args) else None
        args = args[:index] + args[index + 2 :]

    question = " ".join(args)
    if not question or (pinned is None and "--model" in sys.argv):
        print("usage: uv run scripts/ask.py <question> [--model <name>]", file=sys.stderr)
        raise SystemExit(1)

    answer = ask(question, model_name=pinned)

    for name in answer.exhausted:
        print(f"[skipped] {name} is rate limited", file=sys.stderr)
    print(f"[model] {answer.model}", file=sys.stderr)

    for message in answer.messages:
        for call in getattr(message, "tool_calls", []) or []:
            print(f"[tool] {call['name']}({call['args']})")

    print()
    print(text_of(answer.messages[-1]))


if __name__ == "__main__":
    main()
