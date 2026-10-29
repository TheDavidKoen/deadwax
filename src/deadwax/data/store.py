import sqlite3
from collections.abc import Iterable
from datetime import date

from deadwax.data.track import Inferred, Track

SCHEMA = """
CREATE TABLE IF NOT EXISTS tracks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    duration_ms INTEGER NOT NULL,
    release_year INTEGER NOT NULL,
    energy REAL,
    energy_provenance TEXT,
    added_at TEXT NOT NULL,
    last_played_at TEXT
);
CREATE TABLE IF NOT EXISTS track_artists (
    track_id TEXT NOT NULL REFERENCES tracks (id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    artist TEXT NOT NULL,
    PRIMARY KEY (track_id, position)
);
CREATE TABLE IF NOT EXISTS track_genres (
    track_id TEXT NOT NULL REFERENCES tracks (id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    genre TEXT NOT NULL,
    PRIMARY KEY (track_id, position)
);
"""


def connect(path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    return connection


def write_tracks(connection: sqlite3.Connection, tracks: Iterable[Track]) -> None:
    tracks = list(tracks)
    with connection:
        connection.executemany("DELETE FROM tracks WHERE id = ?", [(t.id,) for t in tracks])
        connection.executemany(
            "INSERT INTO tracks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    t.id,
                    t.name,
                    t.duration_ms,
                    t.release_year,
                    t.energy.value if t.energy else None,
                    t.energy.provenance if t.energy else None,
                    t.added_at.isoformat(),
                    t.last_played_at.isoformat() if t.last_played_at else None,
                )
                for t in tracks
            ],
        )
        connection.executemany(
            "INSERT INTO track_artists VALUES (?, ?, ?)",
            [(t.id, n, artist) for t in tracks for n, artist in enumerate(t.artists)],
        )
        connection.executemany(
            "INSERT INTO track_genres VALUES (?, ?, ?)",
            [(t.id, n, genre) for t in tracks for n, genre in enumerate(t.genres)],
        )


def _grouped(connection: sqlite3.Connection, table: str, column: str) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    rows = connection.execute(f"SELECT track_id, {column} FROM {table} ORDER BY track_id, position")
    for track_id, value in rows:
        groups.setdefault(track_id, []).append(value)
    return groups


def _track(row: sqlite3.Row, artists: list[str], genres: list[str]) -> Track:
    return Track(
        id=row["id"],
        name=row["name"],
        artists=tuple(artists),
        duration_ms=row["duration_ms"],
        genres=tuple(genres),
        release_year=row["release_year"],
        energy=(
            Inferred(row["energy"], row["energy_provenance"]) if row["energy"] is not None else None
        ),
        added_at=date.fromisoformat(row["added_at"]),
        last_played_at=(
            date.fromisoformat(row["last_played_at"]) if row["last_played_at"] else None
        ),
    )


def read_tracks(connection: sqlite3.Connection) -> tuple[Track, ...]:
    artists = _grouped(connection, "track_artists", "artist")
    genres = _grouped(connection, "track_genres", "genre")
    cursor = connection.cursor()
    cursor.row_factory = sqlite3.Row
    rows = cursor.execute("SELECT * FROM tracks ORDER BY id")
    return tuple(_track(row, artists.get(row["id"], []), genres.get(row["id"], [])) for row in rows)
