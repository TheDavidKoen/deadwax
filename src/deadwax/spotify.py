import argparse
import os
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from contextlib import closing
from pathlib import Path

from deadwax.config import load_env_file, use_utf8_output
from deadwax.data import library
from deadwax.data.genres import credited_artists, pooled, top_genres
from deadwax.data.sources import Http, artist_with_genres, recordings_by_isrc
from deadwax.data.spotify_api import Spotify, recently_played, saved_tracks
from deadwax.data.spotify_auth import DEFAULT_REDIRECT_URI, access_token, save_token, sign_in
from deadwax.data.spotify_library import build_library, isrc, last_played
from deadwax.data.store import connect, write_tracks

CACHE_DIR = Path(".cache") / "http"
PROGRESS_EVERY = 25


def settings() -> tuple[str, str]:
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    if not client_id:
        raise SystemExit(
            "SPOTIFY_CLIENT_ID is not set. Copy it from your app's settings at "
            "developer.spotify.com/dashboard into .env."
        )
    return client_id, os.environ.get("SPOTIFY_REDIRECT_URI") or DEFAULT_REDIRECT_URI


def musicbrainz_genres(http: Http, saved: Sequence[Mapping]) -> tuple[dict[str, list[str]], int]:
    genres_by_artist: dict[str, list[str]] = {}
    genres_by_track: dict[str, list[str]] = {}
    unmatched = 0
    for number, item in enumerate(saved, start=1):
        code = isrc(item)
        artists = credited_artists(recordings_by_isrc(http, code)) if code else []
        if not artists:
            unmatched += 1
        for mbid in artists:
            if mbid not in genres_by_artist:
                genres_by_artist[mbid] = top_genres(artist_with_genres(http, mbid))
        genres_by_track[item["track"]["id"]] = pooled(genres_by_artist[m] for m in artists)
        if number % PROGRESS_EVERY == 0 or number == len(saved):
            print(f"  tracks {number}/{len(saved)}", file=sys.stderr, flush=True)
    return genres_by_track, unmatched


def run_login() -> None:
    save_token(sign_in(*settings()))
    print("signed in; the token is saved under .cache/ and refreshes itself")


def run_pull(database: Path) -> None:
    spotify = Spotify(access_token(*settings()))

    print("saved tracks ...", file=sys.stderr, flush=True)
    saved = saved_tracks(spotify)
    print(f"  {len(saved)} saved tracks", file=sys.stderr)
    played = last_played(recently_played(spotify))
    print("genres from MusicBrainz, matched by ISRC ...", file=sys.stderr, flush=True)
    genres, unmatched = musicbrainz_genres(Http(CACHE_DIR), saved)

    pulled = build_library(saved, genres, played)
    database.parent.mkdir(parents=True, exist_ok=True)
    database.unlink(missing_ok=True)
    with closing(connect(str(database))) as connection:
        write_tracks(connection, pulled.tracks)

    tagged = Counter(genre for track in pulled.tracks for genre in track.genres)
    untagged = sum(1 for track in pulled.tracks if not track.genres)
    print()
    print(f"{len(pulled.tracks)} tracks written to {database}")
    print(f"{unmatched} tracks have no MusicBrainz recording for their ISRC")
    print(f"{untagged} tracks have no genre")
    print(f"{len(played)} tracks have a last-played date (Spotify only reports the last 50 plays)")
    print(f"most common genres: {', '.join(g for g, _ in tagged.most_common(12)) or 'none'}")
    if pulled.skipped:
        print(f"skipped {len(pulled.skipped)} local or undated tracks: {', '.join(pulled.skipped)}")
    print(f"\nTo use it, add {library.LIBRARY_VARIABLE}={database.as_posix()} to .env")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="deadwax-spotify",
        description="Build a real library database from your Spotify account.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("login", help="sign in to Spotify in the browser and save the token")
    pull = commands.add_parser("pull", help="fetch saved tracks into a SQLite library")
    pull.add_argument("--database", type=Path, default=library.DEFAULT_DATABASE)
    use_utf8_output()
    load_env_file()
    args = parser.parse_args()

    if args.command == "login":
        run_login()
    if args.command == "pull":
        run_pull(args.database)


if __name__ == "__main__":
    main()
