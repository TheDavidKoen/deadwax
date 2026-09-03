from dataclasses import dataclass
from typing import Any

from langchain.agents import create_agent
from langchain_google_genai.chat_models import GoogleRateLimitError

from deadwax.agent.models import build_model, model_order
from deadwax.agent.tools import query_library, validate_playlist

SYSTEM_PROMPT = """You are a librarian for the user's personal music collection.

You answer questions about the library and assemble playlists. You have no knowledge
of what is in the library except what the tools return, so call a tool before every
factual claim.

You never do arithmetic. Counts, totals and durations come from tool results only.
You never decide whether a playlist satisfies its constraints; validate_playlist
decides that.

If a request cannot be satisfied, say so plainly and explain which constraint fails.
Never pad a playlist, substitute something similar, or quietly relax a constraint.

Energy values are estimated rather than measured. If you mention energy, say that it
is an estimate."""


@dataclass(frozen=True)
class Answer:
    model: str
    messages: list[Any]
    exhausted: tuple[str, ...]


def build_agent(model_name: str):
    return create_agent(
        model=build_model(model_name),
        tools=[query_library, validate_playlist],
        system_prompt=SYSTEM_PROMPT,
    )


def ask(question: str, model_name: str | None = None) -> Answer:
    candidates = (model_name,) if model_name else model_order()
    exhausted: list[str] = []

    for name in candidates:
        try:
            result = build_agent(name).invoke({"messages": [{"role": "user", "content": question}]})
        except GoogleRateLimitError:
            exhausted.append(name)
            continue
        return Answer(model=name, messages=result["messages"], exhausted=tuple(exhausted))

    raise RuntimeError(f"every candidate model is rate limited: {', '.join(exhausted)}")
