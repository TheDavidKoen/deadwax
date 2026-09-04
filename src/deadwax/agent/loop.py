from dataclasses import dataclass
from typing import Any

from langchain.agents import create_agent
from langchain_google_genai.chat_models import GoogleRateLimitError

from deadwax.agent import transcript
from deadwax.agent.models import build_model, model_order
from deadwax.agent.tools import check_feasibility, query_library, validate_playlist

MAX_STEPS = 20

SYSTEM_PROMPT = """You are a librarian for the user's personal music collection.

You answer questions about the library and assemble playlists. You have no knowledge
of what is in the library except what the tools return, so call a tool before every
factual claim.

You never do arithmetic. Counts, totals and durations come from tool results only.
You never decide whether a playlist satisfies its constraints; validate_playlist
decides that.

For any playlist request, call check_feasibility first. If it reports feasible false,
say which constraint cannot be met and stop. Do not try track combinations anyway.

When validate_playlist returns ok true, the playlist is correct and you are finished.
Stop calling tools immediately and present that playlist to the user. Do not look for
a better one, do not re-check it, and do not call validate_playlist again.

A duration request is approximate. "A 30 minute playlist" means roughly 30 minutes, so
allow at least a minute either side. Never set min_total_duration_ms equal or nearly
equal to max_total_duration_ms - no set of tracks sums to an exact millisecond target,
and asking for one guarantees failure.

If validate_playlist returns ok false, use the adjust_by amounts to change the track
list and call it again. After three unsuccessful attempts, stop and tell the user which
constraint you could not satisfy.

Never pad a playlist, substitute something similar, or quietly relax a constraint.

Energy values are estimated rather than measured. If you mention energy, say that it
is an estimate."""


@dataclass(frozen=True)
class Answer:
    model: str
    messages: list[Any]
    exhausted: tuple[str, ...]
    converged: bool
    error: str | None

    def tool_calls(self) -> list[dict]:
        return transcript.tool_calls(self.messages)

    def total_tokens(self) -> int:
        return transcript.total_tokens(self.messages)


def build_agent(model_name: str) -> Any:
    return create_agent(
        model=build_model(model_name),
        tools=[check_feasibility, query_library, validate_playlist],
        system_prompt=SYSTEM_PROMPT,
    )


def ask(question: str, model_name: str | None = None, max_steps: int = MAX_STEPS) -> Answer:
    candidates = (model_name,) if model_name else model_order()
    exhausted: list[str] = []

    for name in candidates:
        messages: list[Any] = []
        try:
            for state in build_agent(name).stream(
                {"messages": [{"role": "user", "content": question}]},
                config={"recursion_limit": max_steps},
                stream_mode="values",
            ):
                messages = state["messages"]
        except GoogleRateLimitError:
            exhausted.append(name)
            continue
        except Exception as error:
            return Answer(
                model=name,
                messages=messages,
                exhausted=tuple(exhausted),
                converged=False,
                error=f"{type(error).__name__}: {error}",
            )
        return Answer(
            model=name,
            messages=messages,
            exhausted=tuple(exhausted),
            converged=True,
            error=None,
        )

    raise RuntimeError(f"every candidate model is rate limited: {', '.join(exhausted)}")
