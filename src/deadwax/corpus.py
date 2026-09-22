import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from deadwax.config import use_utf8_output
from deadwax.data import TRACKS
from deadwax.data.resolve import Candidate, Resolution, resolve
from deadwax.data.sources import Http, search_artists

CORPUS_DIR = Path(__file__).parent / "data" / "corpus"
ARTISTS_FILE = CORPUS_DIR / "artists.json"
CACHE_DIR = Path(".cache") / "http"
MUSICBRAINZ_ARTIST = "https://musicbrainz.org/artist/"


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
    use_utf8_output()
    args = parser.parse_args()

    if args.command == "resolve":
        run_resolve(Http(CACHE_DIR))
    if args.command == "approve":
        run_approve()


if __name__ == "__main__":
    main()
