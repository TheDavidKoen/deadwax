from deadwax.data.genres import credited_artists, pooled, top_genres


def credit(mbid: str) -> dict:
    return {"artist": {"id": mbid}}


def test_every_credited_artist_is_found_once_across_recordings():
    recordings = [
        {"artist-credit": [credit("a"), credit("b")]},
        {"artist-credit": [credit("b")]},
    ]
    assert credited_artists(recordings) == ["a", "b"]


def test_no_recording_means_no_artists():
    assert credited_artists([]) == []


def test_the_most_voted_genres_come_first_and_are_capped():
    artist = {
        "genres": [
            {"name": "indie rock", "count": 1},
            {"name": "shoegaze", "count": 7},
            {"name": "dream pop", "count": 7},
            {"name": "noise pop", "count": 2},
        ]
    }
    assert top_genres(artist, limit=3) == ["dream pop", "shoegaze", "noise pop"]


def test_an_artist_with_no_genres_contributes_none():
    assert top_genres({"genres": []}) == []
    assert top_genres({}) == []


def test_genres_are_pooled_across_artists_without_repeats():
    assert pooled([["jazz", "soul"], ["soul", "funk"]]) == ["jazz", "soul", "funk"]
