from dataclasses import replace

import pytest

from deadwax.data import TRACKS
from deadwax.data.store import connect, read_tracks, write_tracks


@pytest.fixture
def connection():
    connection = connect(":memory:")
    yield connection
    connection.close()


def test_the_fixture_library_survives_a_round_trip_unchanged(connection):
    write_tracks(connection, TRACKS)
    assert read_tracks(connection) == tuple(sorted(TRACKS, key=lambda t: t.id))


def test_artists_keep_their_billing_order(connection):
    collaboration = replace(TRACKS[0], artists=("Zed", "Abe"))
    write_tracks(connection, [collaboration])
    assert read_tracks(connection)[0].artists == collaboration.artists


def test_writing_a_track_again_replaces_it_rather_than_duplicating_it(connection):
    track = TRACKS[0]
    write_tracks(connection, [track])
    write_tracks(connection, [replace(track, name="renamed", genres=("only",))])
    stored = read_tracks(connection)
    assert len(stored) == 1
    assert stored[0].name == "renamed"
    assert stored[0].genres == ("only",)


def test_a_track_never_played_is_stored_as_never_played(connection):
    unplayed = next(t for t in TRACKS if t.last_played_at is None)
    write_tracks(connection, [unplayed])
    assert read_tracks(connection)[0].last_played_at is None
