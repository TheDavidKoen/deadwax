# Deadwax

[![CI](https://github.com/TheDavidKoen/deadwax/actions/workflows/ci.yml/badge.svg)](https://github.com/TheDavidKoen/deadwax/actions/workflows/ci.yml)

An agentic music librarian over a personal music library. It answers natural-language
questions about the tracks you have saved, and builds playlists against hard constraints —
with a deterministic validator, a repair loop, and an eval suite that reports pass *rates*
rather than pass/fail.

**[Try the live demo](https://deadwax-demo.onrender.com)** — it runs on a fixed 100-track library, the same data the
eval suite grades. It is on a free server that sleeps when idle, so the first visit can take
about a minute to wake it.

Built as a portfolio piece demonstrating production LLM engineering practice: tool use,
evaluation, tracing, retrieval, real data, an MCP server and a deployed demo.

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
| Live demo | Gradio on a free [Render](https://deadwax-demo.onrender.com) web service — [why not Hugging Face](docs/adr/0012-the-live-demo-runs-on-render.md) |

Stages 0 through 2 use the standard library only — no framework, no SDK, no dependencies.
The raw HTTP call is written by hand before any abstraction is introduced, so that when a
framework misrepresents what it is doing, the difference is visible.

## Running it

You need [git](https://git-scm.com/downloads) and [uv](https://docs.astral.sh/uv/). uv
installs and manages Python itself, so nothing else is required. On Windows:

```bash
winget install --id=astral-sh.uv -e
```

Elsewhere, follow uv's [installation guide](https://docs.astral.sh/uv/getting-started/installation/).
Then:

```bash
git clone https://github.com/TheDavidKoen/deadwax
```

```bash
cd deadwax
```

```bash
uv sync
```

That creates a virtual environment, installs the pinned Python version from
`.python-version`, and installs the project.

Add a free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey). Copy
the template — `copy` on Windows, `cp` elsewhere:

```bash
copy .env.example .env
```

Paste the key after `GEMINI_API_KEY=`, then ask it something:

```bash
uv run deadwax "build me a 30 minute playlist of ambient tracks, nothing over 8 minutes"
```

The model that answered, the library it read, every tool call and, with tracing on, a link
to the trace are printed to stderr, so the answer alone pipes cleanly. `--model` pins a single
model instead of falling back through the free-tier list.

Free-tier limits are per model and differ by an order of magnitude between them. Your
account's actual numbers are at
[aistudio.google.com/rate-limit](https://aistudio.google.com/rate-limit); Google no longer
publishes a per-model table in the API documentation.

### Against your own Spotify library

The fixtures are the default and need no Spotify account. To run the same agent over your own
saved tracks, create an app at [developer.spotify.com](https://developer.spotify.com/dashboard)
with the redirect URI `http://127.0.0.1:8888/callback`, put its client ID in `.env` as
`SPOTIFY_CLIENT_ID`, then:

```bash
uv run deadwax-spotify login
```

```bash
uv run deadwax-spotify pull
```

`login` opens Spotify in the browser, asking for read-only access, using PKCE, so no client
secret exists to leak. `pull` writes `data/library.sqlite`, which is gitignored. Set
`DEADWAX_LIBRARY=data/library.sqlite` in `.env` and every tool reads it instead of the
fixtures; the `[library]` line on stderr says which one answered.

```
$ uv run deadwax "what is my most played song?"
Your library does not track play counts or listening history, so I cannot tell you which
song is your most played.
```

Spotify no longer publishes genres or energy, so genres come from MusicBrainz, matched by
each track's ISRC rather than by name, and energy is left unknown rather than invented. What
the real data lacks, and why each gap stays a gap, is in
[ADR 0010](docs/adr/0010-real-data-comes-from-spotify-and-musicbrainz-by-isrc.md). Spotify's
Development Mode needs the app owner to have Premium; the fixtures need nothing.

### From Claude Code, over MCP

The same four tools are also an MCP server. The repository's `.mcp.json` registers it, so
Claude Code started in the repository root offers to connect. To run it by hand:

```bash
uv run deadwax-mcp
```

It speaks MCP over stdio, reads `.env` like the CLI, and answers from whichever library
`DEADWAX_LIBRARY` selects. The tool descriptions are the agent's own, registered by reference
rather than copied, and the system prompt is sent as the server's instructions. What does not
travel — the repair-loop supervisor, the step limit, the citation check — is in
[ADR 0011](docs/adr/0011-over-mcp-the-client-is-the-agent.md).

### In the browser

`demo/` is the Gradio app behind the [live demo](https://deadwax-demo.onrender.com). Its dependencies are in a
separate `demo` group, so the package itself never installs Gradio. To run it locally:

```bash
uv run --group demo demo/app.py
```

It always answers from the fixtures and always uses `gemini-3.5-flash-lite`, whatever `.env`
says, so the demo runs the model and data the scorecard measures. Beside each answer it shows
the tool calls behind it, and a library table filtered to the tracks the answer rests on. That
table is recomputed in Python from the tool calls, not taken from the model's reply. A daily
question cap, `DEADWAX_DEMO_DAILY_QUESTIONS`, keeps a public demo inside the free tier.

The demo remembers the last three exchanges, so a visitor can answer the agent's follow-up
questions. Only the question and answer text is carried forward, never earlier tool calls, so
every turn fetches its numbers afresh and the repair-loop supervisor never sees a previous
turn's playlist. The eval cases are all single questions, so follow-ups are not measured.

`render.yaml` deploys it to Render once CI passes on `main`, installing exactly the versions
in `uv.lock`. The free service sleeps after 15 idle minutes, and while it sleeps nothing of it
is running to say so; Render shows its own loading page while it wakes. `demo/wake/` is a
branded alternative, published as a separate static site that never sleeps: it explains the
wait, checks every few seconds whether the demo is up, and goes there the moment it is. Why the demo moved from Hugging Face, and what the move costs, is in
[ADR 0012](docs/adr/0012-the-live-demo-runs-on-render.md).

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
yields an empty callback list and everything else runs unchanged. CI has no
secrets, and anyone cloning this repository can run the agent with a Gemini key alone.
Observability that breaks the thing it observes when switched off is not observability.

A chat model is invoked in exactly two places — the agent stream, and the tool-free closing
turn that writes the final answer — and the handler reaches both. Covering only the first
would leave every sentence a user actually reads untraced while the rule appeared satisfied.
The embedding calls behind retrieval are traced too, each as an embedding span.

The eval runner names each trace after its case and attaches the four scores to it, so a red
cell in the scorecard is a filter in the Langfuse UI rather than a hunt. Each recorded attempt
also carries its own `trace_url`, which makes a results file from three weeks ago still
clickable.

```
[trace] https://cloud.langfuse.com/project/<id>/traces/<id>
```

The CLI prints that line to stderr on every run while tracing is on.

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

## Retrieval corpus

Background on every artist in the fixture library — MusicBrainz facts and the English
Wikipedia article — split into 627 chunks and embedded with `gemini-embedding-001`. Search is cosine
similarity in plain Python over a committed file, with
[no vector database](docs/adr/0002-no-vector-database.md).

```bash
uv run deadwax-corpus search "who was the singer in Can"
```

The corpus is a reviewed snapshot rather than something fetched live — see
[ADR 0008](docs/adr/0008-the-retrieval-corpus-is-a-reviewed-snapshot.md). Several artists share
their names with others on MusicBrainz, so every ambiguous match is checked by a person before
any text is fetched, and the eval suite always measures the agent against the same text.

Retrieval reliably finds the right artist, but its similarity scores cannot show whether a
passage actually answers the question: an irrelevant question about Radiohead scores much like
a relevant one about Can. Judging that is left to the model, and the eval suite holds it to it.

### Answering from it

The agent reaches the corpus through one tool, `enrich_artist(artist, question)`, which ranks
only that artist's passages and returns the best four with their sources. Answers cite them by
id, and the CLI turns each citation into a source line:

```
$ uv run deadwax "What is Burial's real name?"
Burial's real name is William Emmanuel Bevan [burial-01].

Sources
[burial-01] Burial, Introduction. https://en.wikipedia.org/wiki/Burial_%28musician%29 (CC BY-SA 4.0)
```

**What the model already knows does not count.** The artists here are famous, so the model
could answer most background questions from training, and an answer from memory looks exactly
like one from retrieval. So only retrieved passages are a source, and when they are silent the
agent says so:

```
$ uv run deadwax "Which films has Jonny Greenwood from Radiohead scored?"
My sources do not cover which films Jonny Greenwood has scored.
```

It almost certainly knows the answer. That reply is less helpful and much more trustworthy,
and it is the one eval case that can only pass if retrieval, not memory, is the source.
Citations are checked in code: a reply that cites a passage the agent was never given fails
its eval case and gets a warning instead of a source line. See
[ADR 0009](docs/adr/0009-the-models-own-knowledge-is-not-a-source.md).

## Evaluation

```bash
uv run evals/runner.py
```

25 cases in `evals/cases/`, each run three times, scored on four dimensions separately.
Cases are TOML read with `tomllib` — a read-only parser, so no code in this repository can
write one at runtime.

The first fifteen were written by hand by the author, before the code they grade was
finished. The eight adversarial cases added at stage 7 were drafted by an assistant against
the fixture data and reviewed by the author, and the two retrieval cases at stage 9 were
drafted by an assistant against the corpus. `evals/cases/README.md` records which is which,
because a suite that grades its own author's code is worth less than one that does not, and
saying so is cheaper than being caught.

`gemini-3.5-flash-lite` pinned. The current suite is 25 cases. Earlier rows used the 15- and
23-case suites and are kept because each was measured against the one before it. A number
from one suite is not comparable to a number from another — the denominator changed on
purpose. The stage 9 sweep is also scored on the 23 older cases alone, which is the
like-for-like comparison with the row above it.

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
| refusal arithmetic fixed | 23 | 100% | 100% | 96% | 100% |
| — | | | | | |
| stage 9 · retrieval | 25 | 100% | 99% | 95% | 100% |
| the same sweep, older 23 cases only | 23 | 100% | 100% | 94% | 100% |
| stage 10 · real data, fixtures still graded | 25 | 100% | 99% | 95% | 100% |
| — | | | | | |
| the never-played filter, with four sentences of description | 25 | 96% | 96% | 92% | 100% |
| **the never-played filter, parameter only** | **25** | **100%** | **100%** | **97%** | **100%** |

The stage 7 and stage 8 rows measure the same behaviour; only the sample differs. The stage 7
sweep lost 4 of 69 attempts to provider `504`s, which are excluded from every rate, while the
stage 8 sweep was the first with zero transport errors.

The two rows after the stage 8 sweep are graded by the same case files.
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

**`never-played-count`** was the suite's longest-standing red case. It asks about play
history, which no tool could filter on. Until stage 9 the agent made up an answer: the 17 September sweep gave 18, 1 and 23
to the same question, and the true count is 41. In the stage 9 sweep it refused all three
times — *"my tools do not track play counts"* — after a prompt change about artist background
that never mentions the library. In the stage 10 sweep it refused twice, and once fetched all
100 tracks and counted the empty `last_played_at` fields itself: *"You have 26 tracks … that
you have never played."* That is rule 1 broken in the open, with a wrong answer to show for
it. The refusals were never a fix.

The fix is a `played` filter on `query_library`, so Python does the counting. It now answers
41, three times out of three. Getting there is the clearest demonstration in this repository
of rule 2. The first version also added four sentences to the tool's description, explaining
when to use the filter. The sweep fixed `never-played-count` and broke two playlist cases on
every run. `high-energy-under-five-minutes` stopped building playlists and asked how long the
playlist should be. `contradictory-duration` was answered as a track search. A control run of
those two cases on the unchanged code passed 6 of 6, so the change was the cause, not the
model drifting overnight. Cutting the text to two sentences fixed one of them. Cutting it to
none fixed both, and the parameter's name alone was enough for the model to use it. Text added
to one tool's description changed how the agent handled requests that never touch that tool.

The parameter alone still moved one routing decision. On the unchanged code,
`contradictory-duration` went to `check_feasibility` 9 times out of 9, and with the new
parameter it goes to `query_library` 3 times out of 3. All three answers say truthfully that no
track is both under 2 minutes and at least 10. One was graded wrong by a bug in its own key —
`"here are"` matched inside *"There are no tracks"* — corrected and rescored for both sweeps,
as recorded in `evals/cases/README.md`. One more says *"0 tracks"*, which the key does not
accept. It stays a miss rather than loosening the key after reading the answer.

On the author's real library, where Spotify supplies only the last 50 plays, the tool adds a
`play_history` note saying so. Asked the same question, the agent answered *"287 tracks …
though note that only your last 50 plays are tracked."* No eval case measures that, because
the fixtures have a complete history and never produce the note.

Stage 9 added the two retrieval cases, and both answered correctly every time. The one
parameter miss is `jonny-greenwood-film-scores`, where one run out of three stopped at "Jonny
Greenwood is not in your library" instead of retrying with Radiohead. The reply was still
honest, so only the parameter check caught it. The one other drop is a refusal in
`hip-hop-playlist-artist-cap` that named the field `min_total_duration_ms` to the user, one
run out of three, in a case that was clean on 17 September. Three runs cannot separate a
regression from variance.

Stage 10 put a SQLite store and a real Spotify library behind the tools, and changed no prompt
and no tool description. On the fixtures every tool returns exactly what it did before, so the
stage 10 sweep is the same inputs graded a second time. The overall scores came out identical,
and three cases still moved:

- `hip-hop-playlist-artist-cap` was clean again.
- `high-energy-under-five-minutes` built a correct playlist once without saying that energy is
  an estimate.
- `never-played-count` produced the invented 26.

That is the clearest picture of variance this suite has produced. The aggregate holds steady
while individual cases move, which is why no single case's change between two sweeps counts
as evidence on its own. One attempt in 75 was lost to a provider `503` and is excluded.

Case keys have been corrected four times, each for grading wording rather than fact, and
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

The code is MIT. See [LICENSE](LICENSE).

The artist corpus in `src/deadwax/data/corpus/` is not covered by that licence. It contains
text from Wikipedia under CC BY-SA 4.0 and data from MusicBrainz under CC0, with every chunk
attributed to its source — see [its README](src/deadwax/data/corpus/README.md).

Built by [David Koen](https://davidkoen.is-a.dev).
