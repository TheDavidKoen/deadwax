# Deadwax

[![CI](https://github.com/TheDavidKoen/deadwax/actions/workflows/ci.yml/badge.svg)](https://github.com/TheDavidKoen/deadwax/actions/workflows/ci.yml)

An agentic music librarian over a personal listening history. It answers natural-language
questions about what you have listened to, and builds playlists against hard constraints —
with a deterministic validator, a repair loop, and an eval suite that reports pass *rates*
rather than pass/fail.

Built as a portfolio piece demonstrating production LLM engineering practice: tool use,
retrieval, tracing, evaluation, and MCP.

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
| Model | Google Gemini Flash, with OpenRouter fallback |
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
| C · Making it good | 7 · Adversarial cases | 🔨 in progress |
| C · Making it good | 8 · Tracing | ⬜ |
| C · Making it good | 9 · Retrieval | ⬜ `v0.9` |
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

## Evaluation

```bash
uv run evals/runner.py
```

15 hand-written cases in `evals/cases/`, each run three times, scored on three dimensions
separately. Cases are TOML read with `tomllib` — a read-only parser, so nothing in this
repository can write one. If the same author wrote the code and the grading, the score means
nothing.

`gemini-3.5-flash-lite` pinned, graded by the same case files before and after:

| | tool selection | parameters | answer content | convergence | tokens per sweep |
| --- | --- | --- | --- | --- | --- |
| `v0.5` baseline | 100% | 100% | 93% | 98% | 106,118 |
| stage 6 · repair loop | 100% | 100% | 89% | **100%** | 72,038 |
| ranking in Python | 100% | 100% | **91%** | **100%** | **68,049** |

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

The remaining answer failures are two, both correct behaviour graded red. `never-played-count`
has no play-history filter to call, so the agent refuses; that is the one case in the suite
proving it refuses rather than confabulates, and it stays red deliberately.
`contradictory-duration` replies *"not possible"* where the case accepts *"impossible"* — a
key that grades wording rather than fact. Neither key has been adjusted to flatter a result,
because correcting grading criteria inside the change being graded produces a number that
cannot be compared to anything.

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
