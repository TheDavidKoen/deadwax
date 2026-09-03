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
| B · The agent | 3 · First tool loop | 🔨 in progress |
| B · The agent | 4 · Measure the wobble | ⬜ |
| B · The agent | 5 · Eval harness | ⬜ `v0.5` |
| C · Making it good | 6 · Repair loop | ⬜ |
| C · Making it good | 7 · Adversarial cases | ⬜ |
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

Paste the key after `GEMINI_API_KEY=`. Then see which models your key can reach, since
free-tier catalogues change without notice:

```bash
uv run scripts/raw_call.py --list
```

Put one of those ids in `.env` as `GEMINI_MODEL`, and make the call:

```bash
uv run scripts/raw_call.py
```

It prints the full request and the full response before extracting the answer. That is the
point of the script — the shapes are worth knowing before a framework hides them.

Your account's actual rate limits are shown at
[aistudio.google.com/rate-limit](https://aistudio.google.com/rate-limit); Google no longer
publishes a per-model free-tier table in the API documentation.

## Evaluation

The eval suite lands at Stage 5. Cases are written by hand and are never generated — if
the same tool writes both the code and the grading, the score means nothing. Scores are
reported as pass rates across repeated runs, because a single pass on a non-deterministic
system is an anecdote.

Any commit that changes a prompt, a tool description or a model carries before/after eval
scores in its message.

## Licence

MIT. See [LICENSE](LICENSE).

Built by [David Koen](https://davidkoen.is-a.dev).
