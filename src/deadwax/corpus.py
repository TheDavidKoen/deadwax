import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from deadwax.agent import tracing
from deadwax.agent.embeddings import embed_documents, embed_query
from deadwax.agent.models import EMBEDDING_DIMENSIONS, embedding_model
from deadwax.config import load_env_file, use_utf8_output
from deadwax.data import TRACKS
from deadwax.data.documents import (
    MUSICBRAINZ_ARTIST,
    document,
    linked_wikipedia_title,
    wikidata_id,
)
from deadwax.data.resolve import Candidate, Resolution, resolve
from deadwax.data.sources import (
    Http,
    english_wikipedia_title,
    lookup_artist,
    search_artists,
    wikipedia_article,
)
from deadwax.retrieval.chunking import chunk_documents
from deadwax.retrieval.index import INDEX_FILE, read_index, write_index
from deadwax.retrieval.search import top_k

CORPUS_DIR = Path(__file__).parent / "data" / "corpus"
ARTISTS_FILE = CORPUS_DIR / "artists.json"
DOCUMENTS_FILE = CORPUS_DIR / "documents.json"
CACHE_DIR = Path(".cache") / "http"


def library_genres() -> dict[str, list[str]]:
    genres: defaultdict[str, set[str]] = defaultdict(set)
    for track in TRACKS:
        for artist in track.artists:
            genres[artist].update(track.genres)
    return {artist: sorted(values) for artist, values in sorted(genres.items())}


def summary(candidate: Candidate) -> dict:
    return {
        "mbid": candidate.mbid,
        "name": candidate.name,
        "disambiguation": candidate.disambiguation,
        "country": candidate.country,
    }


def entry(resolution: Resolution) -> dict:
    chosen = summary(resolution.chosen) if resolution.chosen else None
    return {
        "musicbrainz": chosen,
        "needs_review": resolution.needs_review,
        "reason": resolution.reason,
        "alternatives": [summary(c) for c in resolution.alternatives],
    }


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def describe(candidate: dict) -> str:
    note = candidate.get("disambiguation") or "no note"
    return f"{candidate.get('name')} ({note}, {candidate.get('country') or '??'})"


def print_review(artists: dict) -> None:
    flagged = {name: e for name, e in artists.items() if e["needs_review"]}
    print(f"\n{len(artists)} artists, {len(flagged)} to review\n")
    for name, e in flagged.items():
        chosen = e["musicbrainz"] or {}
        print(f"{name} — {e['reason']}")
        print(f"  picked {describe(chosen)}")
        print(f"         {MUSICBRAINZ_ARTIST}{chosen.get('mbid')}")
        for alt in e["alternatives"]:
            print(f"  passed {describe(alt)}")
        print()


def run_resolve(http: Http) -> None:
    artists = read_json(ARTISTS_FILE)
    for artist, genres in library_genres().items():
        if artist in artists:
            continue
        print(f"  {artist} ... ", end="", flush=True, file=sys.stderr)
        resolution = resolve(artist, genres, search_artists(http, artist))
        artists[artist] = entry(resolution)
        write_json(ARTISTS_FILE, artists)
        print("REVIEW" if resolution.needs_review else "ok", file=sys.stderr)

    print_review(artists)
    print(f"written to {ARTISTS_FILE}")


def run_approve() -> None:
    artists = read_json(ARTISTS_FILE)
    if not artists:
        raise SystemExit(f"{ARTISTS_FILE} does not exist yet. Run 'resolve' first.")

    missing = [name for name, e in artists.items() if e["musicbrainz"] is None]
    if missing:
        raise SystemExit(f"no MusicBrainz match for: {', '.join(missing)}")

    approved = sum(1 for e in artists.values() if e["needs_review"])
    for entry_ in artists.values():
        entry_["needs_review"] = False
        entry_["reviewed"] = True
    write_json(ARTISTS_FILE, artists)
    print(f"{approved} flagged match(es) approved, {len(artists)} artists confirmed")


def run_fetch(http: Http) -> None:
    artists = read_json(ARTISTS_FILE)
    if not artists or any(not e.get("reviewed") for e in artists.values()):
        raise SystemExit(
            "every match must be reviewed first: run 'resolve', check it, then 'approve'"
        )

    documents = read_json(DOCUMENTS_FILE)
    retrieved = date.today().isoformat()
    for name, e in artists.items():
        if name in documents:
            continue
        mbid = e["musicbrainz"]["mbid"]
        print(f"  {name} ... ", end="", flush=True, file=sys.stderr)
        artist = lookup_artist(http, mbid)
        relations = artist.get("relations", [])
        qid = wikidata_id(relations)
        title = english_wikipedia_title(http, qid) if qid else linked_wikipedia_title(relations)
        article = wikipedia_article(http, title) if title else None
        documents[name] = document(name, mbid, artist, article, retrieved)
        write_json(DOCUMENTS_FILE, documents)
        print(article[0] if article else "NO WIKIPEDIA ARTICLE", file=sys.stderr)

    without = [name for name, d in documents.items() if d["wikipedia"] is None]
    print()
    print(f"{len(documents)} documents, {len(documents) - len(without)} with a Wikipedia article")
    if without:
        print(f"no article for: {', '.join(without)}")
    print(f"written to {DOCUMENTS_FILE}")


def run_index() -> None:
    documents = read_json(DOCUMENTS_FILE)
    if not documents:
        raise SystemExit(f"{DOCUMENTS_FILE} does not exist yet. Run 'fetch' first.")

    chunks = chunk_documents(documents)
    print(f"{len(chunks)} chunks from {len(documents)} artists", file=sys.stderr)
    vectors = embed_documents([chunk.text for chunk in chunks])
    write_index(
        INDEX_FILE,
        chunks,
        vectors,
        embedding_model(),
        EMBEDDING_DIMENSIONS,
        date.today().isoformat(),
    )
    print(f"written to {INDEX_FILE}")


def run_search(query: str, k: int) -> None:
    index = read_index()
    if index.model != embedding_model() or index.dimensions != EMBEDDING_DIMENSIONS:
        raise SystemExit(
            f"the index was built with {index.model} at {index.dimensions} dimensions; "
            f"rebuild it with 'index' before searching"
        )
    for hit in top_k(embed_query(query), index.vectors, k):
        chunk = index.chunks[hit.position]
        print(f"{hit.score:.3f}  {chunk.id}  [{chunk.section}]")
        print(f"       {chunk.text.splitlines()[-1][:150]}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="deadwax-corpus",
        description="Build the artist background corpus used for retrieval.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "resolve",
        help="match every library artist to a MusicBrainz id and flag ambiguous matches",
    )
    commands.add_parser(
        "approve",
        help="record that the flagged matches have been checked by a person",
    )
    commands.add_parser(
        "fetch",
        help="download MusicBrainz facts and Wikipedia text for every approved artist",
    )
    commands.add_parser(
        "index",
        help="chunk the documents and embed them into the committed retrieval index",
    )
    search = commands.add_parser("search", help="query the index, to check what it retrieves")
    search.add_argument("query", nargs="+")
    search.add_argument("-k", type=int, default=5, help="how many chunks to show")
    use_utf8_output()
    load_env_file()
    args = parser.parse_args()

    if args.command == "resolve":
        run_resolve(Http(CACHE_DIR))
    if args.command == "approve":
        run_approve()
    if args.command == "fetch":
        run_fetch(Http(CACHE_DIR))
    if args.command == "index":
        run_index()
    if args.command == "search":
        run_search(" ".join(args.query), args.k)
    tracing.flush()


if __name__ == "__main__":
    main()
