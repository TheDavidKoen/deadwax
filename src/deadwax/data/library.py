import os
from contextlib import closing
from functools import cache
from pathlib import Path

from deadwax.data.fixtures import TRACKS, Track
from deadwax.data.store import connect, read_tracks

FIXTURES = "fixtures"
LIBRARY_VARIABLE = "DEADWAX_LIBRARY"
DEFAULT_DATABASE = Path("data") / "library.sqlite"


def source() -> str:
    return os.environ.get(LIBRARY_VARIABLE) or FIXTURES


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
