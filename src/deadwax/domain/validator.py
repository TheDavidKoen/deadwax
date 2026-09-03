from collections import Counter
from collections.abc import Sequence

from deadwax.data import Track
from deadwax.domain.constraints import (
    Constraints,
    Feasibility,
    InfeasibleReason,
    SoftScore,
    ValidationResult,
    Violation,
    ViolationCode,
)


def _duplicate_tracks(tracks: Sequence[Track], constraints: Constraints) -> tuple[Violation, ...]:
    counts = Counter(t.id for t in tracks)
    repeated = tuple(track_id for track_id, n in counts.items() if n > 1)
    if not repeated:
        return ()

    return (
        Violation(
            code=ViolationCode.DUPLICATE_TRACK,
            track_ids=repeated,
            remedy=f"remove {len(repeated)} duplicated track(s)",
        ),
    )


def _tracks_too_long(tracks: Sequence[Track], constraints: Constraints) -> tuple[Violation, ...]:
    limit = constraints.max_track_duration_ms
    if limit is None:
        return ()

    offenders = tuple(t for t in tracks if t.duration_ms > limit)
    if not offenders:
        return ()

    longest = max(t.duration_ms for t in offenders)
    return (
        Violation(
            code=ViolationCode.TRACK_TOO_LONG,
            track_ids=tuple(t.id for t in offenders),
            remedy=f"replace {len(offenders)} track(s) exceeding {limit} ms",
            adjust_by=limit - longest,
        ),
    )


def _genres_not_allowed(tracks: Sequence[Track], constraints: Constraints) -> tuple[Violation, ...]:
    required = set(constraints.required_genres)
    if not required:
        return ()

    offenders = tuple(t for t in tracks if not required & set(t.genres))
    if not offenders:
        return ()

    return (
        Violation(
            code=ViolationCode.GENRE_NOT_ALLOWED,
            track_ids=tuple(t.id for t in offenders),
            remedy=f"replace {len(offenders)} track(s) outside {sorted(required)}",
        ),
    )


def _release_years_out_of_range(
    tracks: Sequence[Track], constraints: Constraints
) -> tuple[Violation, ...]:
    before = constraints.released_before
    after = constraints.released_after
    if before is None and after is None:
        return ()

    offenders = tuple(
        t
        for t in tracks
        if (before is not None and t.release_year >= before)
        or (after is not None and t.release_year <= after)
    )
    if not offenders:
        return ()

    return (
        Violation(
            code=ViolationCode.RELEASE_YEAR_OUT_OF_RANGE,
            track_ids=tuple(t.id for t in offenders),
            remedy=f"replace {len(offenders)} track(s) outside the release window",
        ),
    )


def _artist_limit_exceeded(
    tracks: Sequence[Track], constraints: Constraints
) -> tuple[Violation, ...]:
    limit = constraints.max_tracks_per_artist
    if limit is None:
        return ()

    counts = Counter(artist for t in tracks for artist in t.artists)
    over = {artist: n for artist, n in counts.items() if n > limit}
    if not over:
        return ()

    offenders = tuple(t for t in tracks if set(t.artists) & set(over))
    excess = sum(n - limit for n in over.values())
    return (
        Violation(
            code=ViolationCode.ARTIST_LIMIT_EXCEEDED,
            track_ids=tuple(t.id for t in offenders),
            remedy=f"drop {excess} track(s) by {sorted(over)}",
            adjust_by=-excess,
        ),
    )


def _duration_over(tracks: Sequence[Track], constraints: Constraints) -> tuple[Violation, ...]:
    limit = constraints.max_total_duration_ms
    if limit is None:
        return ()

    total = sum(t.duration_ms for t in tracks)
    if total <= limit:
        return ()

    return (
        Violation(
            code=ViolationCode.DURATION_OVER,
            track_ids=tuple(t.id for t in tracks),
            remedy=f"remove {total - limit} ms",
            adjust_by=limit - total,
        ),
    )


def _duration_under(tracks: Sequence[Track], constraints: Constraints) -> tuple[Violation, ...]:
    minimum = constraints.min_total_duration_ms
    if minimum is None:
        return ()

    total = sum(t.duration_ms for t in tracks)
    if total >= minimum:
        return ()

    return (
        Violation(
            code=ViolationCode.DURATION_UNDER,
            track_ids=tuple(t.id for t in tracks),
            remedy=f"add {minimum - total} ms",
            adjust_by=minimum - total,
        ),
    )


def _energy_score(tracks: Sequence[Track], constraints: Constraints) -> tuple[SoftScore, ...]:
    target = constraints.target_energy
    if target is None or not tracks:
        return ()

    mean = sum(t.energy.value for t in tracks) / len(tracks)
    return (
        SoftScore(
            name="energy",
            score=max(0.0, min(1.0, 1.0 - abs(mean - target))),
            provenance=tracks[0].energy.provenance,
        ),
    )


_CHECKS = (
    _duplicate_tracks,
    _tracks_too_long,
    _genres_not_allowed,
    _release_years_out_of_range,
    _artist_limit_exceeded,
    _duration_over,
    _duration_under,
)


def validate(tracks: Sequence[Track], constraints: Constraints) -> ValidationResult:
    violations = tuple(violation for check in _CHECKS for violation in check(tracks, constraints))
    return ValidationResult(
        ok=not violations,
        violations=violations,
        soft_scores=_energy_score(tracks, constraints),
    )


def _satisfies_track_constraints(track: Track, constraints: Constraints) -> bool:
    disqualifiers = (
        constraints.max_track_duration_ms is not None
        and track.duration_ms > constraints.max_track_duration_ms,
        bool(constraints.required_genres)
        and not set(constraints.required_genres) & set(track.genres),
        constraints.released_before is not None
        and track.release_year >= constraints.released_before,
        constraints.released_after is not None and track.release_year <= constraints.released_after,
    )
    return not any(disqualifiers)


def _max_achievable_ms(candidates: Sequence[Track], max_tracks_per_artist: int | None) -> int:
    if max_tracks_per_artist is None:
        return sum(t.duration_ms for t in candidates)

    used: Counter[str] = Counter()
    total = 0
    for track in sorted(candidates, key=lambda t: t.duration_ms, reverse=True):
        if any(used[artist] >= max_tracks_per_artist for artist in track.artists):
            continue
        for artist in track.artists:
            used[artist] += 1
        total += track.duration_ms
    return total


def check_feasibility(library: Sequence[Track], constraints: Constraints) -> Feasibility:
    candidates = tuple(t for t in library if _satisfies_track_constraints(t, constraints))
    requested = constraints.min_total_duration_ms or 0

    if not candidates:
        return Feasibility(
            feasible=False,
            reason=InfeasibleReason.NO_CANDIDATE_TRACKS,
            candidate_count=0,
            max_achievable_ms=0,
            requested_min_ms=requested,
        )

    max_achievable = _max_achievable_ms(candidates, constraints.max_tracks_per_artist)

    if constraints.min_total_duration_ms is not None and max_achievable < requested:
        return Feasibility(
            feasible=False,
            reason=InfeasibleReason.INSUFFICIENT_TOTAL_DURATION,
            candidate_count=len(candidates),
            max_achievable_ms=max_achievable,
            requested_min_ms=requested,
        )

    return Feasibility(
        feasible=True,
        reason=None,
        candidate_count=len(candidates),
        max_achievable_ms=max_achievable,
        requested_min_ms=requested,
    )
