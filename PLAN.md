# Build Plan

Twelve stages in four phases. Each ends with something runnable and committed.
Do one stage per Claude Code session. Do not start a stage before the previous
one's acceptance criteria pass.

Real Spotify data arrives at stage 10, deliberately. Fixed fixture data keeps the
eval suite stable and keeps you unblocked by API quotas while the interesting work
happens.

---

## Phase A — Ground

### Stage 0: One raw call
Repo, `.env`, Gemini key. A single script that posts to the API with `fetch` and
prints the response. No SDK, no framework.

**Done when:** you can describe the request and response shape from memory.

**Why:** every framework in this space is a wrapper over this. Knowing what is
underneath means you can debug when the wrapper lies.

### Stage 1: Fixture data
`src/data/fixtures.js` — 100 hand-made tracks with id, name, artists, durationMs,
genres, energy, addedAt, lastPlayedAt. Realistic spread: some long, some short,
several tracks per artist, a few recently played.

**Done when:** the fixture set can produce at least one infeasible brief.

### Stage 2: Deterministic core
Port `validator.js`. Unit tests with node:test. No model involved.

**Done when:** tests cover every violation code, plus a feasibility case that
correctly returns `feasible: false`.

---

## Phase B — The agent, and the shock

### Stage 3: First tool loop
Vercel AI SDK. Two tools only: `query_library` and `validate_playlist`. Ask it
plain questions about the fixture library.

**Done when:** the model answers three different questions using the right tool
without you touching the code between them.

### Stage 4: Measure the wobble
Pick one query. Run it 10 times unchanged. Log every tool call and final answer
to a file. Diff them.

**Done when:** you have written a paragraph describing exactly what varied.

**Why:** this is the stage the whole project exists for. Everything after this is
a response to what you see here. Keep the log — it goes in the writeup.

### Stage 5: Eval harness
`evals/runner.js` plus 15 hand-written cases: query, expected tool, expected
parameters, expected answer. Score the three dimensions separately. Run each case
3 times, report pass rate not pass/fail.

**Write these cases yourself.** If Claude Code writes both the code and the
grading, you are marking your own homework with the same pen.

**Done when:** `npm run evals` prints a scorecard and writes JSON to `evals/results/`.

---

## Phase C — Making it good

### Stage 6: Repair loop
Port `repair-loop.js`. Feasibility guard before generation, three repair
attempts, honest failure after.

**Done when:** eval score recorded before and after in the commit message.

### Stage 7: Adversarial cases
Add 8 cases that should fail gracefully: impossible duration, ambiguous brief
needing a clarifying question, query about absent data, constraint contradicting
itself.

**Done when:** you know your pass rate on these, whatever it is. A bad number
here is useful material, not a problem to hide.

### Stage 8: Tracing
Langfuse. Wrap every model call. Attach eval scores to traces.

**Done when:** you can open a failed eval case and read its full trace.

### Stage 9: Retrieval
Artist background text from MusicBrainz and Wikipedia. Chunk, embed at build
time to JSON, cosine similarity search. `enrich_artist` tool. Answers must cite
retrieved chunks.

**Done when:** eval cases exist for "answer is in the corpus" and "answer is not
in the corpus, say so" — and the second one passes.

---

## Phase D — Ship

### Stage 10: Real data
Spotify pull into SQLite, MusicBrainz enrichment. Same interfaces as the
fixtures, so nothing above changes.

**Done when:** evals still run against fixtures, and the app runs against real
data.

### Stage 11: MCP server
Expose the same tools over MCP. Connect Claude Code to it. Screen-record
yourself querying your own library from the terminal.

**Done when:** the recording exists. Half a day, because the tools already exist.

### Stage 12: Site and writeup
Astro pages: the demo, the eval scorecard with before/after chart, the writeup.

Writeup structure — three sections, nothing else:
1. What the eval harness measured
2. What it caught that manual testing did not
3. What changed as a result, with numbers

**Done when:** a stranger reading only the writeup understands what you learned.

---

## Working with Claude Code

- One stage per session. Start each with: "Read CLAUDE.md and PLAN.md. We are on
  stage N."
- Commit at every stage boundary. Tag stages 5, 9 and 12 — those are the
  demonstrable milestones.
- Write eval cases and the writeup yourself, always.
- When it proposes moving a rule check into the prompt, say no. That is rule 1.
- Keep a `NOTES.md` of things that surprised you. That file becomes your
  interview answers.
