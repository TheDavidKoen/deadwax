# 0002 — No vector database

Status: Accepted
Date: 2026-08-26

## Context

Stage 9 adds retrieval over artist background text drawn from MusicBrainz and Wikipedia, so
that the librarian can answer questions its structured library data cannot. The reflexive
choice is a vector database — Pinecone, Weaviate, Chroma, pgvector.

The corpus is a few thousand chunks. At that size, an exhaustive cosine similarity scan
over an in-memory array is measured in single-digit milliseconds. Approximate nearest
neighbour indexes exist to avoid a linear scan; below roughly a hundred thousand vectors
there is no linear scan worth avoiding.

There is a second consideration. This repository is read by people evaluating whether its
author understands retrieval. A dependency that hides the mechanism behind
`index.query(vector, top_k=5)` demonstrates that its author can read a quickstart. Forty
lines implementing chunking, embedding, normalisation and ranking demonstrate that its
author knows what the quickstart is doing.

## Decision

Embeddings are computed at build time and written to a JSON file that ships with the repo.
Search is exhaustive cosine similarity in plain JavaScript. There is no vector database and
no vector index.

Retrieval quality is evaluated, not assumed — Stage 9 requires eval cases for both "the
answer is in the corpus" and "the answer is not in the corpus, say so", and the second one
must pass. An answer that cites no retrieved chunk is a failure regardless of how good the
prose is.

## Consequences

**Good.** Zero infrastructure, zero cost, zero cold start, and the retrieval path is fully
inspectable and unit-testable. Build-time embedding means the deployed site is a static
artifact — no runtime embedding calls, no quota risk in the demo path. Every part of the
pipeline is code we can point at and explain.

**Costly.** The corpus is bounded by what fits in memory and in the repository. Adding a
document means re-running the build, not writing to an index. There is no metadata
filtering, no hybrid search, and no incremental update path.

**Accepted risk.** This choice does not name-match job descriptions that list "vector
databases" as a requirement. That is a real cost and it is being paid deliberately: the
engineering argument is stronger, and the ceiling can be demonstrated separately if it
matters. If the corpus ever exceeds roughly a hundred thousand chunks, or metadata
filtering becomes necessary, this record should be superseded rather than quietly worked
around.
