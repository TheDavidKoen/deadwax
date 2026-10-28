# Artist corpus

Background text about every artist in the fixture library, used by retrieval. Built once by
`deadwax-corpus` and committed, so the agent, the eval suite and CI all read the same snapshot
without network access or an API key.

| file | contents | written by |
| --- | --- | --- |
| `artists.json` | each library artist matched to a MusicBrainz id, with the alternatives that were rejected | `resolve`, then `approve` |
| `documents.json` | MusicBrainz facts and the English Wikipedia article for each artist | `fetch` |
| `index.jsonl` | the documents split into chunks, each with a 768-number embedding | `index` |

## Rebuilding

```bash
uv run deadwax-corpus resolve
uv run deadwax-corpus approve
uv run deadwax-corpus fetch
uv run deadwax-corpus index
```

`resolve` flags any artist whose name MusicBrainz shares with others — there are seven called
Burial — and `fetch` refuses to run until a person has checked those matches and run `approve`.
Every step skips work it has already done and caches every HTTP response and embedding under
`.cache/`, so a rerun is free and an interrupted one resumes where it stopped.

`index` sends one embedding request per chunk. The free tier allows 100 a minute, so the build
is paced and takes about seven minutes from cold.

`tests/retrieval/test_committed_index.py` fails if `index.jsonl` is out of date with
`documents.json`, or was built with a different embedding model from the one configured.

## Sources and licences

Every chunk records the URL it came from and the licence it is under.

- **MusicBrainz** — artist type, area, and begin and end dates, from
  [musicbrainz.org](https://musicbrainz.org). Core data is
  [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
- **Wikipedia** — article text from [en.wikipedia.org](https://en.wikipedia.org), retrieved on the
  date recorded in each document, under
  [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Each article is attributed by
  its URL in `documents.json` and on every chunk in `index.jsonl`. The text is shortened — reference
  sections are dropped and each article is cut at a section boundary after about 8,000 characters
  — but is otherwise unmodified. These files are available under the same licence.
- **Wikidata** is used only to find the right Wikipedia page from a MusicBrainz id. No Wikidata
  content is stored.

The shortening has a consequence worth knowing. Some articles stop before an artist's later
history, so the corpus can lack facts the model already knows from training. That is deliberate
material for the eval suite: an answer must come from what was retrieved, not from memory.
