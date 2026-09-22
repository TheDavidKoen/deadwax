import pytest

from deadwax.data.resolve import normalise, resolve


def result(mbid: str, name: str, score: int = 100, tags: tuple[str, ...] = (), **extra) -> dict:
    return {
        "id": mbid,
        "name": name,
        "score": score,
        "tags": [{"name": tag} for tag in tags],
        **extra,
    }


@pytest.mark.parametrize(
    ("library", "musicbrainz"),
    [
        ("Bjork", "Björk"),
        ("Sigur Ros", "Sigur Rós"),
        ("Neu!", "NEU!"),
        ("D'Angelo", "D\u2019Angelo"),
    ],
)
def test_names_that_differ_only_in_accents_case_or_apostrophes_match(library, musicbrainz):
    assert normalise(library) == normalise(musicbrainz)


def test_a_single_exact_match_needs_no_review():
    resolution = resolve("Slint", ["post-rock"], [result("a", "Slint")])
    assert resolution.chosen.mbid == "a"
    assert resolution.needs_review is False


def test_an_exact_name_beats_a_higher_scoring_near_miss():
    results = [result("near", "Slint Tribute", score=100), result("exact", "Slint", score=90)]
    assert resolve("Slint", ["post-rock"], results).chosen.mbid == "exact"


def test_genre_tags_choose_between_artists_sharing_a_name():
    results = [
        result("prog", "Popol Vuh", tags=("progressive rock",)),
        result("kraut", "Popol Vuh", tags=("krautrock", "ambient")),
    ]
    resolution = resolve("Popol Vuh", ["ambient", "krautrock"], results)
    assert resolution.chosen.mbid == "kraut"
    assert resolution.needs_review is True
    assert "picked by genre tags" in resolution.reason


def test_a_shared_name_the_tags_cannot_separate_is_flagged_as_such():
    results = [result("one", "Gas"), result("two", "Gas")]
    resolution = resolve("Gas", ["ambient"], results)
    assert "do not separate" in resolution.reason


def test_no_exact_match_is_flagged():
    resolution = resolve("Wipers", ["post-punk"], [result("x", "The Wipers Band")])
    assert resolution.needs_review is True
    assert "no exact name match" in resolution.reason


def test_a_low_search_score_is_flagged():
    resolution = resolve("Wire", ["post-punk"], [result("w", "Wire", score=60)])
    assert "score" in resolution.reason


def test_no_results_is_flagged_with_nothing_chosen():
    resolution = resolve("Nobody", [], [])
    assert resolution.chosen is None
    assert resolution.needs_review is True
