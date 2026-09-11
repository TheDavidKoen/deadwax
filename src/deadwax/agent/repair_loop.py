from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from deadwax.agent import transcript
from deadwax.agent.models import build_model

MAX_REPAIR_ATTEMPTS = 3


class Stop(StrEnum):
    VALIDATED = "validated"
    INFEASIBLE = "infeasible"
    UNREPAIRED = "unrepaired"


@dataclass(frozen=True)
class Verdict:
    stop: Stop | None = None
    failures: int = 0
    detail: dict | None = None


CLOSING = {
    Stop.VALIDATED: (
        "The playlist you proposed has passed validation and is correct. Present it to "
        "the user now. List the tracks, and quote track_count and "
        "total_duration_display from the validation result verbatim. Do not round them, "
        "do not hedge, and do not suggest changes."
    ),
    Stop.INFEASIBLE: (
        "This brief cannot be satisfied by the library. Tell the user plainly that it is "
        "not possible, name the constraint that fails, and compare max_achievable_ms "
        "against what they asked for. Do not offer a playlist and do not relax the "
        "constraint."
    ),
    Stop.UNREPAIRED: (
        "Repair attempts are exhausted. Tell the user in plain language which constraint "
        "could not be satisfied and by how much, quoting adjust_by_display where the "
        "violation carries it. Never show a raw millisecond figure, and never repeat a "
        "field name such as remedy or adjust_by back to the user. Do not present a "
        "playlist and do not claim partial success."
    ),
}


def inspect(messages: Sequence[Any]) -> Verdict:
    failures = 0
    for name, result in transcript.tool_results(messages):
        if name == "check_feasibility" and result.get("feasible") is False:
            return Verdict(Stop.INFEASIBLE, failures, result)
        if name != "validate_playlist":
            continue
        if result.get("ok") is True:
            return Verdict(Stop.VALIDATED, failures, result)
        failures += 1
        if failures > MAX_REPAIR_ATTEMPTS:
            return Verdict(Stop.UNREPAIRED, failures, result)
    return Verdict(failures=failures)


def finalise(messages: Sequence[Any], verdict: Verdict, model_name: str) -> Any:
    closing = {"role": "user", "content": CLOSING[verdict.stop]}
    return build_model(model_name).invoke([*messages, closing])
