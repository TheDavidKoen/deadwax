# 0005 — The agent does not decide when it is finished

Status: Accepted
Date: 2026-09-09

## Context

[0004](0004-agent-convergence-is-enforced-in-code.md) moved constraint *validity* into code:
the tool refuses to evaluate an impossible target. It left the *stop condition* in the system
prompt:

> When validate_playlist returns ok true, the playlist is correct and you are finished. Stop
> calling tools immediately.

The `v0.5` eval baseline measured what that instruction was worth. Reading the recorded tool
call sequences for `playlist-max-two-per-artist`:

| run | sequence | converged |
| --- | --- | --- |
| 1 | `check_feasibility`, `query_library`, `validate_playlist` ×8 | no — hit the step ceiling |
| 2 | `check_feasibility`, `query_library`, `validate_playlist` ×6 | yes |
| 3 | `check_feasibility`, `query_library`, `validate_playlist` ×6 | yes |

The convergence rate reported 98%, because only run 1 exhausted its budget. That number
understated the defect by a factor of three: **every** run was re-validating a playlist the
deterministic layer had already passed. Six to eight calls where one was correct.

This is worth separating from 0004's failure. There the model invented an unsatisfiable
constraint and could not succeed. Here it succeeded and kept going anyway. The prompt was
present and explicit in both cases.

An instruction is a request. A model that follows it 100% of the time is not a model that
cannot do otherwise.

## Decision

The control flow leaves the model. A supervisor in `src/deadwax/agent/repair_loop.py` reads
the transcript after every graph step and ends the run itself.

| observed tool result | outcome |
| --- | --- |
| `check_feasibility` → `feasible: false` | `Stop.INFEASIBLE` — refuse before generation, rule 4 |
| `validate_playlist` → `ok: true` | `Stop.VALIDATED` — the playlist is correct, nothing remains |
| a fourth `validate_playlist` → `ok: false` | `Stop.UNREPAIRED` — one proposal plus three repairs, then honest failure, rule 5 |

`ask` breaks out of the LangGraph stream on any of these and makes one closing call against a
model built **without tools bound**, so the finishing turn is structurally incapable of
re-entering the loop it was just pulled out of. The stop reason is recorded on `Answer.stop`
and written into every eval result, which makes "who ended this run" a measurable property
rather than an inference.

`inspect` is a pure function of the message list. It performs no I/O and calls no model, so
the stop logic is unit tested in CI without an API key — the defect above is now a regression
test costing nothing to run.

The system prompt keeps its corresponding instructions, unchanged. They are steering, and
this record exists because steering is not enforcement. Removing them would have been a
second variable in the same experiment.

## Evidence

`gemini-3.5-flash-lite` pinned, 15 cases × 3 runs, graded by the same case files before and
after. `evals/results/gemini-3.5-flash-lite-20260907T143712Z.json` and
`…-20260909T125100Z.json`.

| | before | after |
| --- | --- | --- |
| `validate_playlist` calls, `playlist-max-two-per-artist` | 6.7 avg | **1.0** |
| tokens, that case | 45,106 | **16,889** |
| tokens, whole sweep | 106,118 | **72,038** |
| convergence | 98% | **100%** |
| tool selection / parameters | 100% / 100% | 100% / 100% |
| answer content | 93% | **89%** |

Answer content fell. Of the five failing attempts, three are `never-played-count`, which is
unchanged and correct — `query_library` has no play-history filter and the agent refuses. The
other two:

- `contradictory-duration` replied *"it is **not possible** to fulfil this request"* with the
  exact achievable maximum. The case accepts `"impossible"` and not `"not possible"`. The
  behaviour is right; the closing prompt introduced here shifted the wording, and the key
  grades wording. **This regression is caused by this change.**
- `energy-disclosed-as-estimate` ran with `stop=None`, one tool call, and 3,039 tokens
  against the baseline's 3,043 — a path this change does not touch. It passed three times
  before by chance. `query_library` does not return the `energy` field at all, so the case has
  been green for the wrong reason since it was written, and rule 6 is currently untested.

Both keys were deliberately left unchanged for this measurement. Correcting grading criteria
inside the change being graded produces a number that cannot be compared to anything.

## Consequences

**Good.** The most expensive failure mode in the system is now structurally unreachable
rather than discouraged, at a third less token cost per sweep. Repair still happens — one
`playlist-ambient-feasible` run validated, failed, repaired and passed — but it is bounded by
a counter instead of by the model's patience.

**Costly.** Every terminated run spends one additional model call on the closing turn. That
is a real cost against a free-tier quota, and it introduces a second prompt whose wording
affects the answer dimension, as the `contradictory-duration` regression shows.

**Accepted risk.** `Stop.INFEASIBLE` fires on any `check_feasibility` returning false, not
only inside a playlist brief. `contradictory-duration` is a library query rather than a
playlist request, and the supervisor ended it. The outcome was correct, but the trigger is
broader than the rule it enforces, and a case where refusal is premature would not be
distinguishable from one where it is right.

**What this record does not claim.** The model still chooses the tools, the parameters and
the tracks, and still produces a different wording every time. This removes its authority
over when the work is done, not over how the work is performed.
