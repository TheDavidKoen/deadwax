# 0007 — Where the "model never computes" line falls

Status: Accepted
Date: 2026-09-17
Amends: [0001](0001-the-model-never-computes.md), by clarifying its scope. The decision is unchanged.

## Context

[0001](0001-the-model-never-computes.md) says all arithmetic, threshold evaluation and rule
checking happens in Python. Three times since, the rule has turned out to be broader than it
was being read, and once it has turned out to be narrower.

**Ranking is a calculation.** Asked for the longest track, the agent read a list of twenty
tracks and picked one — two tool calls and 11,200 tokens to perform a comparison. Nobody had
thought of "find the maximum" as arithmetic. `query_library` gained an `order_by` computed in
Python.

**Formatting a number is a calculation.** An audit of recorded answers found that 11 of 12
refusals converted milliseconds to minutes themselves, because `check_feasibility` returned
only `max_achievable_ms` and the closing prompt said *"compare max_achievable_ms against what
they asked for."* Several conversions were wrong:

> *"Max achievable duration: **22.5 minutes** (1,355,000 ms)"* — the real figure is 22:35
>
> *"At least **25 minutes** (1,440,000 milliseconds)"* — 1,440,000 ms is 24 minutes

Every one of those answers graded green, because no case forbade raw milliseconds. The
failure 0001 was written to prevent — a confident, well-formed answer containing the wrong
number — had come back through presentation rather than adjudication.

**Echoing an internal value is a presentation error too.** The 24-minute figure above was
not a bad conversion; it was a correct conversion of the wrong number. The system prompt
tells the model to allow a minute's slack on a duration request, so it asked feasibility for
24 minutes, and the tool echoed that back as `requested_min_ms`. Converting it faithfully
would still have told the user *"you asked for 24:00"*.

**Synonyms are not a calculation.** Asked for rap, the agent searched `genre="rap"`, found
nothing, and said so — the nine tracks are tagged `hip hop`. The obvious fix was a synonym
table in Python. That would have been wrong: whether "rap" means "hip hop", or whether
"reggae" should include dub, is a judgement about language, and 0001 assigns language to the
model.

## Decision

**Any value a user reads is produced in Python, in the form the user reads it.** A tool that
returns a duration also returns its display form — `duration_display`,
`total_duration_display`, `adjust_by_display`, `max_achievable_display` — and every prompt
that shows the user a number names the display field, never the raw one. The model is never
asked to convert, round or reformat.

**Values the model supplied are described in the user's words, not echoed.** The refusal
prompt tells the model to describe what the user asked for in their own terms and to quote
only what the library can provide. No display field is added for `requested_min_ms`, because
formatting it would lend authority to the wrong number.

**Comparison, ordering and scoring are calculations.** They happen in the tool. Energy is
scored by the validator against a `target_energy` the model chooses, and the score returns
with its provenance, so the disclosure rule 6 requires has data to stand on rather than a
line in the prompt.

**Interpretation stays with the model, and the tool supplies the vocabulary.** When a genre
search finds nothing, `query_library` returns `known_genres`, the tags the library actually
uses. The tool description allows retrying with a tag that is *another name* for the user's
word and forbids *"a genre that is merely related."* No synonym table exists in the code.

## Evidence

`gemini-3.5-flash-lite` pinned, 23 cases × 3 runs, both sweeps graded against the same case
files and zero transport errors on either. The "before" is the committed stage 8 sweep
rescored against the corrected cases, at no API cost.

| | tool | parameters | answer content | convergence |
| --- | --- | --- | --- | --- |
| before | 100% | 96% | 71% | 100% |
| after | 100% | **100%** | **96%** | 100% |

| case | before | after |
| --- | --- | --- |
| `are-there-any-rap-songs` | parameters 0%, answer 0% | **100%, 100%** |
| `high-energy-under-five-minutes` | 0% | **100%** |
| `playlist-jazz-impossible` | 0% | **100%** |
| `reggae-playlist-impossible` | 0% | **100%** |
| `contradictory-duration` | 0% | **100%** |
| `hip-hop-playlist-artist-cap` | 33% | **100%** |

Every refusal now quotes a figure like *"9:51"* taken from a display field. Every
high-energy playlist reports *"an energy score of 0.985 … this score rests on estimated
values"* — a number the model did not compute, with provenance it did not invent.

The vocabulary did not tempt the model into swapping in related genres: `counts-techno` never
reached for "electronic", `reggae-playlist-impossible` never reached for dub, and
`radiohead-jazz-tracks` never searched under "art rock".

## Consequences

**Good.** The boundary is now stated in terms that can be checked mechanically: if a number
appears in an answer, a field produced it. That made the defect above findable by a substring
check on recorded transcripts, and it will make the next one findable the same way.

**Costly.** Every numeric field a tool returns now wants a display twin, and every prompt that
mentions a number must name the right one. That is more surface to keep consistent, and the
`TRACK_TOO_LONG` code was missed on the first pass for exactly that reason.

**Accepted risk.** Leaving synonyms to the model means it can still map too widely. The rule
against substituting a "merely related" genre is steering, not enforcement. The eval cases
that would catch a wrong mapping — `counts-techno`, `reggae-playlist-impossible`,
`radiohead-jazz-tracks` — are the enforcement, and they are only as good as their keys.

**Also changed.** Giving the agent the vocabulary changed its behaviour beyond the case it was
aimed at. `radiohead-jazz-tracks` went from one tool call to two in every run: after finding
no jazz, the agent looked up what the Radiohead tracks actually are, so it could explain.
Better answers, and they broke a key that banned the track names — see
`evals/cases/README.md`. A tool description change moves more than the case it was written
for, which is why rule 2 requires a full sweep.
