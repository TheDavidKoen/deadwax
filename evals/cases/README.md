# Eval cases

One TOML file per case. The filename is the case name, so it appears in the scorecard —
`counts-jazz-tracks.toml` reads better in a report than `case-07.toml`.

The runner reads them with `tomllib`, which is read-only by design: no code in this
repository can write a case file at runtime.

## Who wrote these

A suite whose cases and code came from the same author proves only that the author is
self-consistent, so provenance is recorded rather than assumed.

| cases | author |
| --- | --- |
| the original fifteen, stages 5 and 6 | written by hand by the author, before the code they grade was finished |
| the eight adversarial cases, stage 7 | drafted by an assistant against the fixture data at the author's instruction, then reviewed by the author |

The stage 7 eight are `are-there-any-rap-songs`, `radiohead-jazz-tracks`,
`high-energy-under-five-minutes`, `no-bpm-in-library`, `reggae-playlist-impossible`,
`exact-duration-demanded`, `hip-hop-playlist-artist-cap` and `unknown-track-asked-about`.

Read their scores with that in mind. An assistant drafting a case against data it has just
inspected is likelier to assert what the system already does than what it ought to do, which
is the specific bias the original hand-written rule existed to avoid.

## Schema

```toml
query = "how many jazz tracks do I have?"

[expect]
tool = "query_library"

[expect.parameters]
genre = "jazz"

[expect.answer]
must_contain = ["9"]
must_not_contain = ["approximately", "about"]
```

Every key except `query` is optional. Omit a section and that dimension always passes, which
is the right choice when a case is not about it.

| key | meaning |
| --- | --- |
| `query` | what to ask, verbatim |
| `expect.tool` | a tool that must be called at least once. One of `check_feasibility`, `query_library`, `validate_playlist` |
| `expect.parameters` | arguments that must appear together on one call to that tool. A subset — extra arguments are allowed |
| `expect.answer.must_contain` | facts that must appear in the reply, matched case-insensitively |
| `expect.answer.must_not_contain` | text that must not appear |

## Why answers are graded on facts rather than sentences

Ten identical runs produced nine different wordings — see
[ADR 0004](../../docs/adr/0004-agent-convergence-is-enforced-in-code.md) and the samples in
`evals/variance/`. A grader comparing sentences would report failures that are only
rephrasing.

So assert the things that must be true: a number, a track name, the word "cannot". Not the
shape of the sentence around them.

`must_not_contain` is the sharper tool of the two. It catches hedging on facts the system
knows exactly — "roughly 30 minutes" when the validator returned `30:10` is a real failure,
and the only way to catch it is to forbid the hedge.

### When the right answer is "none", assert the negative

Three attempts at a positive key for `qotsa` scored 0%, 67% and 67% against a system that was
correct every time. The model said "there are no songs by...", then "I found 0...", then
something else again. Every phrasing was right; the key kept missing.

There are many correct ways to say nothing was found and only one way to be wrong: **naming a
track that does not exist**. So assert that instead —

```toml
[expect.answer]
must_not_contain = ["no one knows", "go with the flow", "little sister"]
```

Real titles by that artist, none of which are in the library. Scored 100% immediately,
because it stopped grading English and started grading the failure it actually cares about.

## Three dimensions, scored separately

**Tool selection**, **parameter extraction** and **answer content** are reported as separate
pass rates, because they fail differently. The right tool with wrong arguments is a different
bug from the wrong tool, and a single number hides which one you have.

Each case runs three times by default and reports a **pass rate**, not pass/fail. One pass on
a system measured to be non-deterministic is an anecdote.

## Writing a good case

Cases that only confirm what already works are wasted. The useful ones ask what *should*
happen in situations nobody has coded for yet:

- A brief the library cannot satisfy. Should it name the failing constraint?
- A question about something absent entirely.
- A vague request. Should it guess, or ask a clarifying question?
- Two constraints that contradict each other.

A case you expect to fail is worth more than one you expect to pass. The failures are the
findings.

## Running them

```bash
uv run evals/runner.py --fixtures-only
```

Validates every case parses and names a real tool. No API key, no model calls — this is what
CI runs.

```bash
uv run evals/runner.py
```

The real thing. 15 cases at 3 repeats is 45 runs. Measured from a recorded sweep, that is
**125 requests** — 2.8 model calls per run, not the 5 originally assumed. Count them from the
results file rather than estimating; free-tier budgets are small enough that the difference
decides whether a sweep fits in a day.

```bash
uv run evals/runner.py --case counts-jazz-tracks --repeats 1
```

One case once, while drafting it.

```bash
uv run evals/runner.py --rescore evals/results/<file>.json
```

Re-grades a recorded sweep against the current cases, with **no API calls**. The runner
stores every tool call and reply, not just a verdict, so correcting an answer key costs
nothing — fix the key, rescore, done. Use this rather than re-running 225 requests to find
out whether your fix worked.
