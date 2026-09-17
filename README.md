# Deadwax

[![CI](https://github.com/TheDavidKoen/deadwax/actions/workflows/ci.yml/badge.svg)](https://github.com/TheDavidKoen/deadwax/actions/workflows/ci.yml)

An agentic music librarian over a personal listening history. It answers natural-language
questions about what you have listened to, and builds playlists against hard constraints —
with a deterministic validator, a repair loop, and an eval suite that reports pass *rates*
rather than pass/fail.

Built as a portfolio piece demonstrating production LLM engineering practice: tool use,
evaluation and tracing today, with retrieval and an MCP server still to come — see
[build progress](#build-progress).

## The interesting part

Most LLM demos work until you run them twice. Deadwax is built around what happens on the
second run.

The system is split down one line: **the model never computes.** It interprets language,
chooses tools, and composes prose. Every arithmetic operation, threshold check and
constraint adjudication happens in plain Python that has no idea an LLM exists. When a
playlist violates a constraint, the validator does not return `False` — it returns a
violation code, the offending track ids, and a concrete remedy, which is the only reason
an automated repair loop can work at all.

Feasibility is checked *before* generation. If a brief cannot be satisfied, the system
says so. It never pads, substitutes, or silently degrades — `status="infeasible"` is a
correct outcome with its own eval cases.

## Architecture rules

Not stylistic preferences. Violating any of these defeats the purpose of the project.

1. The model never computes.
2. Tool descriptions are behaviour control — they are prompts, not documentation. Changing
   one is a behavioural change and is re-evaluated before merging.
3. Violations are machine-actionable: a code, the offending ids, a remedy. Never a bare
   boolean, never prose alone.
4. Feasibility is checked before generation.
5. Failure is a valid outcome.
6. Hard constraints are measured and enforced. Soft constraints are inferred and scored,
   and carry a `provenance` field that any message about them must disclose.
7. No model call without a trace.

Decisions and their trade-offs are recorded in [docs/adr](docs/adr).

## Stack

Everything runs on a free tier. That is a hard constraint, not a preference.

| Layer | Choice |
| --- | --- |
| Language | Python 3.13 |
| Toolchain | uv for dependencies and Python itself, ruff for lint and format, pytest |
| Agent | LangChain, introduced at stage 3 and not before |
| Model | Google Gemini Flash, falling back across Gemini free-tier models. OpenRouter fallback is planned, not built |
| Store | SQLite via the `sqlite3` standard library module |
| Retrieval | Build-time embeddings, cosine similarity in plain Python — [no vector database](docs/adr/0002-no-vector-database.md) |
| Tracing | Langfuse |
| Interop | Model Context Protocol server |
| Site | Astro on Cloudflare Pages, static — [the one JavaScript component](docs/adr/0003-python-for-the-agent.md) |
| Live demo | Gradio on a Hugging Face Space, free CPU tier |

Stages 0 through 2 use the standard library only — no framework, no SDK, no dependencies.
The raw HTTP call is written by hand before any abstraction is introduced, so that when a
framework misrepresents what it is doing, the difference is visible.

## Build progress

Twelve stages, four phases. One branch and one squash-merged PR per stage, so the history
reads as the build actually happened.

| Phase | Stage | Status |
| --- | --- | --- |
| A · Ground | 0 · One raw call | ✅ |
| A · Ground | 1 · Fixture data | ✅ |
| A · Ground | 2 · Deterministic core | ✅ |
| B · The agent | 3 · First tool loop | ✅ |
| B · The agent | 4 · Measure the wobble | ✅ |
| B · The agent | 5 · Eval harness | ✅ `v0.5` |
| C · Making it good | 6 · Repair loop | ✅ |
| C · Making it good | 7 · Adversarial cases | ✅ |
| C · Making it good | 8 · Tracing | ✅ |
| C · Making it good | 9 · Retrieval | 🔨 in progress `v0.9` |
| D · Ship | 10 · Real data | ⬜ |
| D · Ship | 11 · MCP server | ⬜ |
| D · Ship | 12 · Site and writeup | ⬜ `v1.0` |

## Running it

You need [uv](https://docs.astral.sh/uv/). It installs and manages Python itself, so it is
the only prerequisite.

```bash
winget install --id=astral-sh.uv -e
```

Then, from the repository root:

```bash
uv sync
```

That creates a virtual environment, installs the pinned Python version from
`.python-version`, and installs the project.

Add a free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey):

```bash
copy .env.example .env
```

Paste the key after `GEMINI_API_KEY=`, then ask it something:

```bash
uv run deadwax "build me a 30 minute playlist of ambient tracks, nothing over 8 minutes"
```

Tool calls and the model that served the request are printed to stderr, so the answer alone
pipes cleanly. `--model` pins a single model instead of falling back through the free-tier
list.

Free-tier limits are per model and differ by an order of magnitude between them. Your
account's actual numbers are at
[aistudio.google.com/rate-limit](https://aistudio.google.com/rate-limit); Google no longer
publishes a per-model table in the API documentation.

## Measuring variance

The same question does not produce the same trajectory twice, so the repository ships the
harness that measures it rather than asserting a number:

```bash
uv run scripts/measure_variance.py "build me a 30 minute playlist" --runs 10
```

It pins one model — a sample spread across models measures the models, not the system —
throttles below the provider's per-minute ceiling, and writes every tool call and answer to
`evals/variance/` after each run rather than at the end, so an interrupted sample keeps what
it has.

Two recorded samples are committed as the evidence behind
[ADR 0004](docs/adr/0004-agent-convergence-is-enforced-in-code.md):
`2026-09-04-before-fixes.json` and `2026-09-04-after-fixes.json`.

## Tracing

Every model call goes through [Langfuse](https://langfuse.com) — rule 7, and the one rule
that stayed unticked from stage 5 to stage 8.

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

**Tracing is optional and the project runs without it.** With no keys set, `tracing.traced`
yields an empty callback list and nothing else in the codebase branches on it. CI has no
secrets, and anyone cloning this repository can run the agent with a Gemini key alone.
Observability that breaks the thing it observes when switched off is not observability.

There are exactly two places a model is invoked — the agent stream, and the tool-free closing
turn that writes the final answer — and the handler reaches both. Covering only the first
would leave every sentence a user actually reads untraced while the rule appeared satisfied.

The eval runner names each trace after its case and attaches the four scores to it, so a red
cell in the scorecard is a filter in the Langfuse UI rather than a hunt. Each recorded attempt
also carries its own `trace_url`, which makes a results file from three weeks ago still
clickable.

```
[trace] https://cloud.langfuse.com/project/<id>/traces/<id>
```

The CLI prints that line to stderr on every run.

### A known false alarm

**A `LangGraph` span marked `ERROR` means the supervisor halted a *successful* run.** Nothing
failed. `ask` breaks out of `.stream()` the moment `validate_playlist` returns `ok: true`,
which closes the generator mid-flight, and LangChain reports the chain as errored.

The correlation is exact: runs that stop early are `ERROR`, runs that finish on their own are
`DEFAULT`. Which makes the signal backwards — a well-behaved playlist run is flagged, while
`are-there-any-rap-songs`, which genuinely gives up, sits there clean.

The trace's root span and its four scores carry the truth; the `LangGraph` level does not.
The real fix is to halt from inside the graph rather than breaking the generator from outside,
which is a redesign of [ADR 0005](docs/adr/0005-the-agent-does-not-decide-when-it-is-finished.md)'s
mechanism and needs its own eval run.

Worth recording how this was found: tracing surfaced it within ten minutes of being switched
on, and it was a defect in code written two stages earlier that every eval sweep had scored as
correct — because it *is* correct. The behaviour was right and the reporting was wrong, and
nothing without traces would have shown that.

## Evaluation

```bash
uv run evals/runner.py
```

23 cases in `evals/cases/`, each run three times, scored on three dimensions separately.
Cases are TOML read with `tomllib` — a read-only parser, so no code in this repository can
write one at runtime.

The first fifteen were written by hand by the author, before the code they grade was
finished. The eight adversarial cases added at stage 7 were drafted by an assistant against
the fixture data and reviewed by the author. `evals/cases/README.md` records which is which,
because a suite that grades its own author's code is worth less than one that does not, and
saying so is cheaper than being caught.

`gemini-3.5-flash-lite` pinned. The current suite is 23 cases; the three rows above the rule
are the 15-case suite, kept because each was measured against the one before it. A number
from a 23-case run is not comparable to one from a 15-case run — the denominator changed on
purpose.

| | cases | tool selection | parameters | answer content | convergence |
| --- | --- | --- | --- | --- | --- |
| `v0.5` baseline | 15 | 100% | 100% | 93% | 98% |
| stage 6 · repair loop | 15 | 100% | 100% | 89% | 100% |
| ranking in Python | 15 | 100% | 100% | 91% | 100% |
| — | | | | | |
| stage 7 · adversarial | 23 | 100% | 97% | 88% | 100% |
| stage 8 · tracing | 23 | 100% | 96% | 87% | 100% |
| — | | | | | |
| stage 8, rescored against corrected cases | 23 | 100% | 96% | 71% | 100% |
| **refusal arithmetic fixed** | **23** | **100%** | **100%** | **96%** | **100%** |

The stage 7 and stage 8 rows measure the same behaviour; only the sample differs. The stage 7
sweep lost 4 of 69 attempts to provider `504`s, which are excluded from every rate, while the
stage 8 sweep was the first with zero transport errors.

The last two rows are the most recent comparison, and both are graded by the same case files.
An audit found that the refusal cases never checked for raw milliseconds, and 11 of 12 refusal
answers contained them. Adding that check and rescoring the committed stage 8 sweep — at no
API cost — dropped its answer content from 87% to 71%. That drop is not a regression. It is
the old number being measured properly for the first time.

That is what the `err` column is for. Read it before the percentages: rates computed over a
short sample are weaker, and burying that would make every other number less trustworthy.

Stage 6 took the stop condition out of the system prompt and put it in code — see
[ADR 0005](docs/adr/0005-the-agent-does-not-decide-when-it-is-finished.md). The case that
motivated it, `playlist-max-two-per-artist`, went from an average of 6.7 `validate_playlist`
calls per run to exactly 1, and from 45,106 tokens to 16,889.

Then `query_library` gained an `order_by` computed in Python. Finding a longest track or a
highest-energy one is a comparison, and a comparison is a calculation — asking the model to
scan a list for a maximum breaks rule 1 as surely as asking it to add. `longest-track`
dropped from two calls and 11,200 tokens to one call and 4,528. Exposing `energy` with its
`provenance` alongside took `energy-disclosed-as-estimate` from 67% to 100%, and for the
right reason: it had been passing on the model repeating a line from the system prompt about
a field the tool never returned.

Stage 7 added eight cases chosen to be hard, and they found three real defects. All three are
now fixed; [ADR 0007](docs/adr/0007-where-the-model-never-computes-line-falls.md) covers why
each fix sits where it does.

- **Refusals did arithmetic.** Every refusal converted milliseconds to minutes by hand, and
  some got it wrong — *"22.5 minutes (1,355,000 ms)"* for a figure of 22:35. Tools now return
  display forms of every number a user reads, and refusals quote them: *"the most this
  library can provide is 9:51."*
- **Rule 6 was unreachable.** The validator could score energy, but no tool let the agent ask
  it to. `validate_playlist` now takes `target_energy`, and the score comes back with its
  provenance: *"an energy score of 0.985 … this score rests on estimated values."*
- **The agent didn't know the library's vocabulary.** Asked for rap, it searched `rap`, found
  nothing and stopped — there are nine tracks tagged `hip hop`. A genre search that misses now
  returns the tags the library uses, and the model decides whether the user's word is another
  name for one. No synonym table exists in code, because that judgement is about language.

One case stays red on purpose. **`never-played-count`** has no play-history filter to call, so
the agent refuses — it is the one case proving the system refuses rather than confabulates.

Case keys have been corrected three times, each for grading wording rather than fact, and
each recorded in `evals/cases/README.md`. Every correction was applied to the "before" sweep
as well as the "after", so the comparison holds.

The dimensions are scored separately because they fail differently: the right tool with the
wrong argument is a different bug from the wrong tool, and one number hides which you have.
Rates, not pass/fail, because a single pass on a system measured to be non-deterministic is
an anecdote.

Any commit that changes a prompt, a tool description or a model carries before/after scores
in its message.

```bash
uv run evals/runner.py --fixtures-only
```

Validates every case without an API key. This is what CI runs, and it has already caught an
empty case file and a tool-name typo before either cost a request.

## Licence

MIT. See [LICENSE](LICENSE).

Built by [David Koen](https://davidkoen.is-a.dev).
