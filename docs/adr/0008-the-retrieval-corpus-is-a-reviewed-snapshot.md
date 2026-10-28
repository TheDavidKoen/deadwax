# 0008 — The retrieval corpus is a reviewed, committed snapshot

Status: Accepted
Date: 2026-10-28

## Context

Stage 9 gives the agent background text about each artist: MusicBrainz facts and the English
Wikipedia article, split into chunks and embedded so the relevant passages can be found by
similarity. Three questions had to be settled before any of it was built.

**Which artist is meant?** MusicBrainz has seven artists called Burial, eight called Cluster
and two called Can, one of them a Korean duo. A plain Wikipedia lookup for "Can" finds the
article about tin cans. Picking the wrong one would not fail loudly; it would quietly describe
a Dutch death metal band when asked about a dubstep producer, and every answer built on it
would be confidently wrong.

**Should the corpus be rebuilt or stored?** Wikipedia changes daily. A corpus rebuilt next
month would shift beneath eval cases written against this one, so a passing case could start
failing with no change to the code. CI has no network access and no API key.

**What does the embedding quota allow?** The free tier counts every text as one request and
allows 100 a minute. The first build failed after exactly 100 texts, two batches of 50 sent
seconds apart, because batching reduces round trips but not the quota.

## Decision

**A person approves every artist match before anything is fetched.** `resolve` matches each
library artist to a MusicBrainz id, choosing between same-named artists by comparing
MusicBrainz's community genre tags with the genres on the library's tracks, and flags every
ambiguous choice with the alternatives it rejected. `fetch` refuses to run until `approve` has
been run. The match then reaches Wikipedia through Wikidata's link from the MusicBrainz id,
never through a title search.

**The corpus is committed.** `artists.json`, `documents.json` and `index.jsonl` are tracked
files, rebuilt only on purpose. A test fails if the index is out of date with the documents or
was built with a different embedding model, so the snapshot cannot silently drift from the
code that reads it.

**Every network result is cached, and every step resumes.** HTTP responses and embeddings are
cached on disk under `.cache/`, keyed by request or by model, dimensions, task and text. An
interrupted build resumes where it stopped and a rerun costs nothing. Embedding is paced at 90
texts a minute.

**Every chunk carries its source and licence.** MusicBrainz data is CC0; Wikipedia text is
CC BY-SA 4.0 and requires attribution. A chunk names its artist and section in its own text,
so a retrieved passage about recording an album in a castle says whose album it was.

## Consequences

**Good.** The eval suite measures the agent against fixed text, so a change in score means a
change in the agent. The matching is checkable: every rejected alternative is recorded beside
the choice. When stage 10 brings a real Spotify library with hundreds of artists nobody chose
by hand, the review step is already in place.

**Costly.** The index is 5.5 MB of committed floating-point numbers, and each rebuild adds
another copy to the repository's history. Text is shortened at about 8,000 characters per
article to keep that bounded.

**Accepted risk.** The snapshot goes stale. That is the intended trade: stale and fixed is
testable, fresh and moving is not. Rebuilding is one command when a newer snapshot is worth
the churn.

**What this record does not settle.** Retrieval finds the right artist reliably, but its
similarity scores do not show whether a passage answers the question. *"What is Radiohead's
favourite food?"* scored 0.705 against Radiohead's introduction; *"who was the singer in
Can?"* scored 0.736 against a passage that answers it. No threshold separates those. Deciding
whether retrieved text contains an answer is a judgement about language, so under
[0001](0001-the-model-never-computes.md) it belongs to the model, and the eval suite is what
holds the model to it.
