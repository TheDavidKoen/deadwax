import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from langfuse import get_client, propagate_attributes
from langfuse.langchain import CallbackHandler

CREDENTIALS = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")


@dataclass(frozen=True)
class Trace:
    callbacks: list[Any]
    id: str | None
    url: str | None


def enabled() -> bool:
    return all(os.environ.get(name) for name in CREDENTIALS)


@contextmanager
def traced(name: str, **attributes: Any) -> Iterator[Trace]:
    if not enabled():
        yield Trace(callbacks=[], id=None, url=None)
        return

    client = get_client()
    with (
        propagate_attributes(trace_name=name, **attributes),
        client.start_as_current_observation(name=name, as_type="agent"),
    ):
        trace_id = client.get_current_trace_id()
        yield Trace(
            callbacks=[CallbackHandler()],
            id=trace_id,
            url=client.get_trace_url(trace_id=trace_id),
        )


def record_scores(trace_id: str | None, scores: Mapping[str, bool]) -> None:
    if trace_id is None or not enabled():
        return

    client = get_client()
    for name, value in scores.items():
        client.create_score(
            name=name,
            value=int(value),
            trace_id=trace_id,
            data_type="BOOLEAN",
        )


def flush() -> None:
    if enabled():
        get_client().flush()
