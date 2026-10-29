import os
from contextlib import closing
from functools import cache
from pathlib import Path

from deadwax.data.fixtures import TRACKS
from deadwax.data.store import connect, read_tracks
from deadwax.data.track import Track

FIXTURES = "fixtures"
LIBRARY_VARIABLE = "DEADWAX_LIBRARY"
DEFAULT_DATABASE = Path("data") / "library.sqlite"
PARTIAL_PLAY_HISTORY = (
    "only the user's last 50 plays are known, so a track counted as never played may "
    "have been played before them"
)


def source() -> str:
    return os.environ.get(LIBRARY_VARIABLE) or FIXTURES


def play_history() -> str | None:
    return None if source() == FIXTURES else PARTIAL_PLAY_HISTORY


@cache
def load(name: str) -> tuple[Track, ...]:
    if name == FIXTURES:
        return TRACKS
    if not Path(name).exists():
        raise FileNotFoundError(
            f"{LIBRARY_VARIABLE} points at {name}, which does not exist. "
            f"Build it with 'deadwax-spotify pull', or set {LIBRARY_VARIABLE}={FIXTURES}."
        )
    with closing(connect(name)) as connection:
        return read_tracks(connection)


def tracks() -> tuple[Track, ...]:
    return load(source())
