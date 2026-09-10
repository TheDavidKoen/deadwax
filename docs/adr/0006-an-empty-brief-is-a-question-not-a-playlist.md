# 0006 — An empty brief is a question, not a playlist

Status: Accepted
Date: 2026-09-10

## Context

[0005](0005-the-agent-does-not-decide-when-it-is-finished.md) ends a run when
`validate_playlist` returns `ok: true`, on the reasoning that a validated playlist is
finished work. Measuring an unrelated change to `query_library` exposed the flaw in that
reasoning.

Asked *"make me a playlist"* — no length, no genre, no artist, nothing — the agent produced:

```
query_library(limit=20)
check_feasibility()
validate_playlist(track_ids=["t001", "t003", "t004", "t005"])
```

Every call carries an empty constraint set. The validator had nothing to check, so it
returned `ok: true`. That tripped `Stop.VALIDATED`, and the closing prompt then *instructed*
the model to present the playlist as correct. It shipped four Radiohead tracks, with a track
count and a duration, for a request that specified neither.

Nothing here misbehaved by its own rules. The validator answered the question it was asked.
The supervisor did what 0005 says. The failure is that **a trivially satisfiable constraint
set is indistinguishable from a satisfied one**, and the machinery built to make success
authoritative made a vacuous success authoritative too.

The sweep that recorded this was discarded for unrelated reasons — a provider outage
invalidated 14 of its 45 attempts — so the sequence above is quoted from it rather than
cited. The case had scored 100% at stage 6 and 0% here; the richer tool description was
enough to tip the model from asking a question into calling the tools.

## Decision

Neither tool will act on a brief that constrains nothing.

- `validate_playlist` with no duration bounds, no per-artist limit and no required genres
  returns `ok: false` with `invalid_constraints` and a remedy naming what to ask the user
  for. This follows the existing degenerate-duration-window guard: where a request cannot be
  meaningfully evaluated, the tool declines to evaluate it rather than returning a
  meaningless pass.
- `check_feasibility` with an empty brief returns `needs_clarification`, **deliberately not
  `feasible: false`.**

The second half of that matters more than it looks. `feasible: false` would trip
`Stop.INFEASIBLE`, whose closing prompt tells the model to state plainly that the request
cannot be satisfied and name the failing constraint. That is the wrong answer. *"I cannot
build that playlist"* is false; *"how long would you like it, and what should be in it?"* is
correct. A refusal and a question are different outcomes and the shape of the tool result is
what distinguishes them, so `test_an_empty_brief_does_not_end_the_run_as_infeasible` pins it
against a future change to that guard.

## Consequences

**Good.** Rule 4 — feasibility is checked before generation — now covers the case where there
is nothing to check. The system cannot invent a specification and then congratulate itself
for meeting it, which is the most plausible way an agent over a library would embarrass its
author in front of a user.

**Costly.** "Constrains nothing" is a judgement, and a user who genuinely wants an arbitrary
playlist is refused and asked a question instead. That is the same trade as
`MIN_DURATION_WINDOW_MS` in [0004](0004-agent-convergence-is-enforced-in-code.md), and it
goes the same way: an unconstrained request is far more often an underspecified one than a
deliberate one.

**Accepted risk.** The guard sits at the tool boundary, so it only fires on a model that
calls the tools. Nothing stops one improvising a playlist straight out of `query_library`
results and never validating it at all. That failure mode is unaddressed here and would need
enforcement outside the tools.

**What this record does not claim.** The eval sweep taken after this change did not exercise
the guard. All three `vague-playlist-request` runs asked a clarifying question without
calling any tool, which is the desired behaviour but arrived at by the model's choice rather
than by enforcement. The guard is verified by unit tests only. That is the honest status: the
hole is closed in code, and the measurement has not yet had occasion to prove it.
