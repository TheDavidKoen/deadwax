# 0001 — The model never computes

Status: Accepted
Date: 2026-08-26
Amended: 2026-08-27 by [0003](0003-python-for-the-agent.md), implementation language only.
The decision itself is unchanged.

## Context

Deadwax builds playlists against hard constraints: total duration within a window, no more
than *n* tracks per artist, every track released before a given year. A language model is
capable of producing a playlist that looks like it satisfies those constraints, and is not
capable of guaranteeing that it does.

The failure mode is specific and nasty. The model does not fail loudly — it returns a
confident, well-formed, plausible answer whose durations sum to the wrong number. Nobody
notices until someone adds it up. Wrapping the model in a more emphatic prompt
("be careful to check the total duration") reduces the frequency of this without changing
its nature, which makes it worse: rarer bugs are harder to find, not less harmful.

The same shape appears in every constraint-satisfaction domain the target problems come
from — underwriting limits, eligibility rules, dosage thresholds. The question is not
whether a model can usually get arithmetic right. It is whether "usually" is an acceptable
guarantee for a rule that has a definite answer.

## Decision

All arithmetic, threshold evaluation, rule checking and constraint adjudication happens in
deterministic Python. The model interprets natural language, selects tools, and
composes prose. It does nothing else.

Concretely:

- The validator is a pure function with no I/O and no model access. It can be unit tested
  exhaustively, and it is.
- Feasibility is computed before generation, not asserted afterwards.
- The model is never asked to confirm that a constraint holds. It is told, by code, whether
  it holds.
- Any inferred quantity — energy, mood — is explicitly a *soft* constraint, is scored
  rather than enforced, and carries a `provenance` field so that no message can present an
  inference as a measurement.

## Consequences

**Good.** Constraint correctness stops being a probabilistic property of the prompt and
becomes a property of tested code. The eval suite can then measure the things that are
genuinely uncertain — tool selection, parameter extraction, answer quality — instead of
drowning in arithmetic failures. The validator's output being machine-actionable (a code,
the offending ids, a remedy) is what makes an automated repair loop possible at all; a
bare `false` gives the repair loop nothing to act on.

**Costly.** Every new constraint type needs deterministic code, not a sentence added to a
prompt. This is slower to build and is meant to be. It is the boundary that makes the
system explainable, and moving a rule check into a prompt to save an afternoon is the one
change that would quietly turn this project back into a demo.

**Accepted risk.** The natural-language-to-constraint translation step remains the model's
job and remains fallible. A misread brief produces a correctly-validated playlist that
answers the wrong question. This is mitigated by evaluating parameter extraction as its
own scored dimension, and by clarifying questions on ambiguous briefs — not by pretending
the risk is gone.
