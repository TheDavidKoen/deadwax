# 0010 — Real data comes from Spotify, with genres from MusicBrainz by ISRC

Status: Accepted
Date: 2026-10-28

## Context

Stage 10 replaces the hand-built fixtures with the author's own Spotify library, behind the
same interface, so that nothing in the agent, the tools or the validator changes. The plan
assumed Spotify's Web API would supply everything a `Track` needs. By October 2026 it does
not.

**What Spotify still provides.** Saved tracks (`GET /me/tracks`) with exact durations, release
dates and each track's ISRC, plus the last 50 plays from `GET /me/player/recently-played`.

**What Spotify withholds.**

- **Energy.** Audio features were removed for new apps in November 2024.
- **Genres.** `GET /artists/{id}` no longer returns a `genres` field at all. Observed on
  2026-10-28 across all 257 artists in the library: the response carries only `id`, `name`,
  `images`, `href`, `uri` and `external_urls`. The February 2026 migration guide does not
  mention this.
- **Listening history.** Only the last 50 plays are available.
- **Batch lookups.** `GET /tracks` and `GET /artists` were removed in February 2026, so every
  lookup is one request.

**Who can use it.** Since February 2026 a Development Mode app works only while its owner has
Spotify Premium, and is limited to five users. That is acceptable for a single-user demo
whose owner already subscribes. It would not be acceptable as a requirement for running the
project, so the fixtures stay the default and need no Spotify account at all.

## Decision

**The library comes from Spotify's saved tracks, read once into SQLite.** `deadwax-spotify
pull` writes `data/library.sqlite`, which is gitignored so personal listening data never
reaches the public repository. `DEADWAX_LIBRARY` selects it; unset, the tools read the
fixtures. The eval runner and the variance script force the fixtures, so a real library
configured in `.env` can never change a score.

**Sign-in uses PKCE with no client secret.** The flow is written with the standard library:
a verifier and challenge per RFC 7636, the browser for consent, and a one-request local server
for the redirect. The scopes are read-only. There is no secret to leak.

**Durations and release years come from Spotify** and are measured, so they stay hard
constraints, exactly as in the fixtures.

**Genres come from MusicBrainz, matched by ISRC rather than by name.** Each track's ISRC
identifies one MusicBrainz recording, the recording names its credited artists by MusicBrainz
id, and each artist's three most-voted genres are pooled. No step compares names, so the
collisions that made stage 9a's resolver need a human review — seven artists called Burial —
cannot occur, and no review gate is needed. ISRCs are normalised before lookup: Spotify
returned four in lower case, which MusicBrainz rejects.

**What is missing stays missing.** Energy is `None` with a provenance that says no estimate
exists, never a default value; the validator scores only tracks that have an estimate. A track
with no MusicBrainz match has no genres, not a guessed one. A track absent from the last 50
plays has no `last_played_at`.

## Consequences

**Genre coverage is partial and reported.** On the first pull, 203 of 294 tracks have genres.
76 ISRCs have no MusicBrainz recording, and some matched artists have no genres yet. Those
tracks never match a genre search. A fallback that searched MusicBrainz by artist name would
close some of the gap and bring back exactly the ambiguity this decision avoids.

**Genres are community labels treated as hard constraints.** MusicBrainz genres are voted, not
measured. They are kept hard because they are recorded metadata that the system looks up,
not values a model inferred, which is the line
[architecture rule 6](../../README.md#architecture-rules) draws. The fixtures' genres were hand-authored and treated the same way.

**"Never played" means "not in the last 50 plays"** on real data. The agent cannot tell the
difference from the data alone. Spotify's privacy export contains the full history and would
fix this; it is not used yet.

**Artist background does not cover the real library.** The retrieval corpus from
[ADR 0008](0008-the-retrieval-corpus-is-a-reviewed-snapshot.md) was built for the fixture
artists. On real data `enrich_artist` finds no passages for most artists, and its message
calls them "outside the user's library", which is no longer accurate. Correcting that changes
a tool result the eval cases depend on, so it needs its own sweep.

**Spotify can change again, and only one module would notice.** The tools read `Track`s from
the store. Everything Spotify-shaped lives in `data/spotify_api.py`, `data/spotify_auth.py` and
the pure mapping in `data/spotify_library.py`.
