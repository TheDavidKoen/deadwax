# 0009 — The model's own knowledge is not a source

Status: Accepted
Date: 2026-10-28

## Context

Stage 9 gives the agent an `enrich_artist` tool that returns passages from the committed
corpus described in [ADR 0008](0008-the-retrieval-corpus-is-a-reviewed-snapshot.md). The
artists in this library are famous enough that the model already knows a great deal about
most of them from training, which creates a problem retrieval alone does not solve.

**An answer from memory and an answer from retrieval look identical.** Ask who sang for Can
and the model gives the same names either way. Nothing in a correct-looking reply shows
whether it came from the passages or from training, so neither a user nor an eval can tell
whether retrieval is doing anything.

**Memory and the corpus disagree.** Articles are cut at a section boundary, so Can's stops in
1979 and the corpus records only MusicBrainz's "dissolved in 1991". Wikipedia dates
Radiohead's formation to 1985; MusicBrainz says 1991. A model free to mix the two produces
answers that match neither source and cannot be checked against either.

**Similarity scores do not measure answerability.** Stage 9a found that an irrelevant
question about Radiohead scores much like a relevant one about Can, because the passages
really are about Radiohead. No threshold separates "found the answer" from "found the band".

## Decision

**For artist background, only the retrieved passages count as a source.** The system prompt
says so in one sentence, and the `enrich_artist` description says it again where the model
reads the passages: answer only from these, and if they do not answer the question, say your
sources do not cover it, *even if you believe you know*.

**Every claim cites a passage id**, such as `[burial-01]`, and the citations are checked in
code, not trusted:

- `retrieval/citations.py` extracts cited ids from the reply. It is pure and has no I/O.
- The eval runner fails the answer for any case whose reply cites an id the agent was never
  given, and a case can set `must_cite = true` to require at least one citation.
- The CLI prints a source line for each cited passage, with its URL and licence, which also
  meets the attribution term of Wikipedia's CC BY-SA licence. A fabricated id gets a warning
  instead of a source line.

**Retrieval is limited to one artist before similarity is computed.** The tool takes an artist
name, matched ignoring case and accents, and ranks only that artist's passages. Similarity
then only orders passages that are already about the right subject, which is the job 9a showed
it can do.

**Scores are not returned to the model.** A number the model cannot interpret correctly is an
invitation to apply a threshold it should not, so whether a passage answers the question is
left as a language judgement, consistent with [ADR 0001](0001-the-model-never-computes.md).

## Consequences

**The agent will decline questions it could answer.** Asked which films Jonny Greenwood has
scored, it says its sources do not cover them, though it almost certainly knows. In the short
term that is a worse answer for the user. It is a *checkable* one, and the eval case for it,
`jonny-greenwood-film-scores`, can only pass if retrieval is actually the source.

**The habit spreads to the library.** `never-played-count` asks about play history, which no
tool can filter on. Before this change the agent made up a count; in the 17 September sweep it
answered 18, 1 and 23 to the same question. After it, it refuses all three times — *"my tools
do not track play counts"*. That is better behaviour from a prompt that never mentions the
library, and it is still a failing case, because the data exists and the fix is a filter.

**Citations are measured, not enforced at runtime.** An uncited reply reaches the user with no
source lines. The supervisor ([ADR 0005](0005-the-agent-does-not-decide-when-it-is-finished.md))
could reject it and ask again, but that is another closing turn and another request per answer
on a free tier, so it waits until the eval suite shows uncited answers happening.

**A non-library name ends the search.** The tool refuses artists outside the library and lists
the known ones. In one run out of three the agent stopped there for Jonny Greenwood instead of
retrying with Radiohead. The answer was still honest, so content passed and only the parameter
check caught it.
