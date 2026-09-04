from collections.abc import Sequence
from typing import Any


def answer_text(message: Any) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    return "".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )


def tool_calls(messages: Sequence[Any]) -> list[dict]:
    return [
        {"name": call["name"], "args": call["args"]}
        for message in messages
        for call in (getattr(message, "tool_calls", None) or [])
    ]


def total_tokens(messages: Sequence[Any]) -> int:
    return sum(
        (getattr(message, "usage_metadata", None) or {}).get("total_tokens", 0)
        for message in messages
    )
