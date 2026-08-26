# Music Librarian Agent

An agentic system over a personal music library. Answers natural-language questions
about listening history and builds playlists against hard constraints, with a
deterministic validator and a measured eval suite.

Built as a portfolio piece demonstrating production LLM engineering practice.

## Stack

- Runtime: Node.js, ESM, vanilla JavaScript. No TypeScript.
- Agent layer: Vercel AI SDK
- Model: Google Gemini Flash (free tier) with OpenRouter fallback
- Store: SQLite (better-sqlite3), local file
- Retrieval: build-time embeddings, cosine similarity in plain JS. No vector database.
- Tracing: Langfuse (free tier)
- Frontend: Astro, vanilla JS, deployed to Cloudflare Pages
- Everything must run on free tiers.

## Architecture rules

These are not stylistic preferences. Violating them defeats the purpose of the project.

1. **The model never computes.** Any arithmetic, threshold, rule check or
   constraint adjudication happens in deterministic JavaScript. The model
   interprets language, chooses tools, and composes prose. Nothing else.

2. **Tool descriptions are behaviour control.** They are prompts, not
   documentation. Changing one is a behavioural change and must be re-evaluated
   against the eval suite before merging.

3. **Violations are machine-actionable.** The validator returns a code, the
   offending track ids, and a concrete remedy. Never a bare boolean, never prose
   alone.

4. **Feasibility is checked before generation.** If a brief cannot be satisfied,
   the system reports that. It never pads, substitutes, or degrades silently.

5. **Failure is a valid outcome.** `status: 'infeasible'` and
   `status: 'unrepaired'` are correct behaviours with their own eval cases.

6. **Hard vs soft constraints.** Anything measured is hard and enforced. Anything
   inferred (energy, mood) is soft and scored. Inferred values carry a
   `provenance` field and any message about them says so.

7. **No model call without a trace.** Every call goes through the traced wrapper.

## Code conventions

- No code comments. Names and structure carry the meaning.
- Pure functions for anything deterministic. The validator has no I/O.
- Model calls isolated to `src/agent/`. Nothing else imports the AI SDK.
- Never hardcode a model name outside `src/agent/models.js`. Free-tier
  catalogues change without notice and the router must fall back.

## Layout

```
src/
  data/          fixture data, ingest scripts, SQLite access
  domain/        validator, feasibility, constraint types. Pure, no I/O.
  agent/         models, tools, repair loop, tracing wrapper
  retrieval/     chunking, embedding, search
  mcp/           MCP server exposing the same tools
evals/
  cases/         hand-written eval cases. Never generated.
  runner.js      scores a run, writes results/
web/             Astro site
```

## Rules for working on this repo

- Eval cases in `evals/cases/` are written by hand by the author. Do not generate,
  extend or edit them. They are the ground truth that grades the code.
- Any change to a prompt, tool description or model must be accompanied by an
  eval run before and after, with both scores recorded in the commit message.
- Do not add dependencies without asking. The free-tier constraint is a hard
  requirement of the project.
