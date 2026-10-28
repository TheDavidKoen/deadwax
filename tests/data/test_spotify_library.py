from datetime import date

from deadwax.data.spotify_library import build_library, isrc, last_played, release_year


def saved(
    track_id: str | None,
    name: str = "Song",
    artists: tuple[tuple[str, str], ...] = (("a1", "Artist"),),
    release_date: str = "1997-05-21",
    is_local: bool = False,
    code: str | None = "GBAYE9700001",
) -> dict:
    return {
        "added_at": "2024-03-01T10:00:00Z",
        "track": {
            "id": track_id,
            "name": name,
            "artists": [{"id": i, "name": n} for i, n in artists],
            "duration_ms": 240_000,
            "album": {"release_date": release_date},
            "is_local": is_local,
            "external_ids": {"isrc": code} if code else {},
        },
    }


def played(track_id: str, when: str) -> dict:
    return {"track": {"id": track_id}, "played_at": when}


def test_a_release_year_is_read_from_any_date_precision():
    assert release_year({"release_date": "1997-05-21"}) == 1997
    assert release_year({"release_date": "1997-05"}) == 1997
    assert release_year({"release_date": "1997"}) == 1997


def test_an_unknown_release_date_has_no_year():
    assert release_year({"release_date": "0000"}) is None
    assert release_year({}) is None


def test_the_most_recent_play_of_a_track_wins():
    recent = [played("t1", "2026-10-01T08:00:00Z"), played("t1", "2026-10-20T08:00:00Z")]
    assert last_played(recent) == {"t1": date(2026, 10, 20)}


def test_the_isrc_is_read_from_the_external_ids():
    assert isrc(saved("t1", code="GBAYE9700001")) == "GBAYE9700001"
    assert isrc(saved("t1", code=None)) is None


def test_an_isrc_in_the_wrong_case_or_with_hyphens_is_normalised():
    assert isrc(saved("t1", code="ushm91744629")) == "USHM91744629"
    assert isrc(saved("t1", code="GB-AYE-97-00001")) == "GBAYE9700001"


def test_a_malformed_isrc_is_treated_as_missing():
    assert isrc(saved("t1", code="not-an-isrc")) is None


def test_a_saved_track_becomes_a_library_track():
    pulled = build_library([saved("t1", name="Airbag")], {"t1": ["art rock"]}, {})
    track = pulled.tracks[0]
    assert (track.id, track.name, track.artists) == ("t1", "Airbag", ("Artist",))
    assert (track.duration_ms, track.release_year, track.genres) == (240_000, 1997, ("art rock",))
    assert track.added_at == date(2024, 3, 1)


def test_a_track_has_no_energy_rather_than_an_invented_one():
    assert build_library([saved("t1")], {}, {}).tracks[0].energy is None


def test_a_track_with_no_known_genre_has_none():
    assert build_library([saved("t1")], {}, {}).tracks[0].genres == ()


def test_only_tracks_in_the_recent_plays_have_a_last_played_date():
    pulled = build_library([saved("t1"), saved("t2")], {}, {"t1": date(2026, 10, 20)})
    assert [t.last_played_at for t in pulled.tracks] == [date(2026, 10, 20), None]


def test_local_and_undated_tracks_are_skipped_and_reported():
    items = [
        saved("t1"),
        saved(None, name="Local demo", is_local=True),
        saved("t3", name="Old", release_date="0000"),
    ]
    pulled = build_library(items, {}, {})
    assert [t.id for t in pulled.tracks] == ["t1"]
    assert pulled.skipped == ("Local demo", "Old")
