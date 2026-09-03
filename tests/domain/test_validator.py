import pytest

from deadwax.data import TRACKS
from deadwax.domain.constraints import Constraints, InfeasibleReason, ViolationCode
from deadwax.domain.validator import check_feasibility, validate

BY_ID = {track.id: track for track in TRACKS}

JAZZ_BRIEF = Constraints(
    min_total_duration_ms=60 * 60 * 1000,
    max_track_duration_ms=6 * 60 * 1000,
    required_genres=("jazz",),
)


def playlist(*track_ids: str) -> list:
    return [BY_ID[track_id] for track_id in track_ids]


@pytest.mark.parametrize(
    ("track_ids", "constraints", "expected"),
    [
        pytest.param(
            ("t001", "t001"),
            Constraints(),
            ViolationCode.DUPLICATE_TRACK,
            id="the_same_track_twice",
        ),
        pytest.param(
            ("t002",),
            Constraints(max_track_duration_ms=300_000),
            ViolationCode.TRACK_TOO_LONG,
            id="a_track_longer_than_the_cap",
        ),
        pytest.param(
            ("t001",),
            Constraints(required_genres=("jazz",)),
            ViolationCode.GENRE_NOT_ALLOWED,
            id="a_track_outside_the_required_genre",
        ),
        pytest.param(
            ("t002",),
            Constraints(released_after=1970),
            ViolationCode.RELEASE_YEAR_OUT_OF_RANGE,
            id="a_track_released_too_early",
        ),
        pytest.param(
            ("t001", "t003", "t004"),
            Constraints(max_tracks_per_artist=2),
            ViolationCode.ARTIST_LIMIT_EXCEEDED,
            id="three_tracks_by_one_artist_when_two_allowed",
        ),
        pytest.param(
            ("t002",),
            Constraints(max_total_duration_ms=60_000),
            ViolationCode.DURATION_OVER,
            id="a_playlist_longer_than_the_window",
        ),
        pytest.param(
            ("t001",),
            Constraints(min_total_duration_ms=3_600_000),
            ViolationCode.DURATION_UNDER,
            id="a_playlist_shorter_than_the_window",
        ),
    ],
)
def test_hard_constraint_breach_is_reported(track_ids, constraints, expected):
    result = validate(playlist(*track_ids), constraints)

    assert not result.ok
    assert expected in [violation.code for violation in result.violations]


def test_a_satisfied_playlist_passes():
    result = validate(playlist("t001"), Constraints(max_track_duration_ms=300_000))

    assert result.ok
    assert result.violations == ()


def test_violation_names_the_offending_tracks():
    result = validate(playlist("t001", "t002"), Constraints(max_track_duration_ms=300_000))
    violation = result.violations[0]

    assert violation.track_ids == ("t002",)
    assert "t001" not in violation.track_ids


def test_violation_carries_a_machine_actionable_magnitude():
    result = validate(playlist("t002"), Constraints(max_total_duration_ms=60_000))
    violation = result.violations[0]

    assert violation.code is ViolationCode.DURATION_OVER
    assert violation.adjust_by is not None
    assert violation.adjust_by < 0
    assert violation.adjust_by == 60_000 - BY_ID["t002"].duration_ms


def test_inferred_energy_is_scored_and_never_enforced():
    result = validate(playlist("t001", "t003"), Constraints(target_energy=0.5))

    assert result.ok
    assert result.violations == ()
    assert len(result.soft_scores) == 1
    assert result.soft_scores[0].name == "energy"
    assert result.soft_scores[0].provenance


def test_an_impossible_brief_is_infeasible_before_generation():
    outcome = check_feasibility(TRACKS, JAZZ_BRIEF)

    assert outcome.feasible is False
    assert outcome.reason is InfeasibleReason.INSUFFICIENT_TOTAL_DURATION
    assert outcome.candidate_count == 2
    assert outcome.max_achievable_ms < outcome.requested_min_ms


def test_a_brief_with_no_candidate_tracks_is_infeasible():
    outcome = check_feasibility(TRACKS, Constraints(required_genres=("polka",)))

    assert outcome.feasible is False
    assert outcome.reason is InfeasibleReason.NO_CANDIDATE_TRACKS
    assert outcome.candidate_count == 0


def test_an_achievable_brief_is_feasible():
    outcome = check_feasibility(
        TRACKS,
        Constraints(min_total_duration_ms=30 * 60 * 1000, required_genres=("ambient",)),
    )

    assert outcome.feasible is True
    assert outcome.reason is None
    assert outcome.max_achievable_ms >= outcome.requested_min_ms


def test_an_artist_limit_lowers_what_is_achievable():
    unlimited = check_feasibility(TRACKS, Constraints(required_genres=("jazz",)))
    limited = check_feasibility(
        TRACKS, Constraints(required_genres=("jazz",), max_tracks_per_artist=1)
    )

    assert limited.max_achievable_ms < unlimited.max_achievable_ms
