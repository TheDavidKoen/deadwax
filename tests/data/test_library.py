from contextlib import closing

import pytest

from deadwax.agent.tools import query_library
from deadwax.data import TRACKS, library
from deadwax.data.store import connect, write_tracks


def test_the_fixtures_are_the_default(monkeypatch):
    monkeypatch.delenv(library.LIBRARY_VARIABLE, raising=False)
    assert library.tracks() is TRACKS


def test_a_database_named_in_the_environment_is_read_instead(monkeypatch, tmp_path):
    path = tmp_path / "library.sqlite"
    with closing(connect(str(path))) as connection:
        write_tracks(connection, TRACKS[:3])
    monkeypatch.setenv(library.LIBRARY_VARIABLE, str(path))
    assert [t.id for t in library.tracks()] == sorted(t.id for t in TRACKS[:3])


def test_the_tools_read_whichever_library_is_selected(monkeypatch, tmp_path):
    path = tmp_path / "library.sqlite"
    with closing(connect(str(path))) as connection:
        write_tracks(connection, TRACKS[:3])
    monkeypatch.setenv(library.LIBRARY_VARIABLE, str(path))
    assert query_library.invoke({})["total_matching"] == 3


def test_a_missing_database_says_how_to_build_it(monkeypatch, tmp_path):
    monkeypatch.setenv(library.LIBRARY_VARIABLE, str(tmp_path / "absent.sqlite"))
    with pytest.raises(FileNotFoundError, match="deadwax-spotify pull"):
        library.tracks()
