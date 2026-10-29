from collections.abc import Sequence
from dataclasses import dataclass

MAX_EXCHANGES = 3


@dataclass(frozen=True)
class Exchange:
    question: str
    answer: str


def remember(
    history: Sequence[Exchange], exchange: Exchange, limit: int = MAX_EXCHANGES
) -> tuple[Exchange, ...]:
    return (*history, exchange)[-limit:] if limit else ()


def opening_messages(question: str, history: Sequence[Exchange] = ()) -> list[dict]:
    earlier = [
        message
        for exchange in history
        for message in (
            {"role": "user", "content": exchange.question},
            {"role": "assistant", "content": exchange.answer},
        )
    ]
    return [*earlier, {"role": "user", "content": question}]
