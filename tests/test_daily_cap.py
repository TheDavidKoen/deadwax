from concurrent.futures import ThreadPoolExecutor
from datetime import date

from deadwax.daily_cap import DailyCap

MONDAY = date(2026, 10, 26)
TUESDAY = date(2026, 10, 27)


def test_questions_are_allowed_up_to_the_limit():
    cap = DailyCap(limit=2)
    assert [cap.take(MONDAY) for _ in range(3)] == [True, True, False]


def test_the_count_starts_again_the_next_day():
    cap = DailyCap(limit=1)
    cap.take(MONDAY)
    assert cap.take(MONDAY) is False
    assert cap.take(TUESDAY) is True


def test_remaining_counts_down_and_resets():
    cap = DailyCap(limit=3)
    assert cap.remaining(MONDAY) == 3
    cap.take(MONDAY)
    assert cap.remaining(MONDAY) == 2
    assert cap.remaining(TUESDAY) == 3


def test_a_refused_question_is_not_counted():
    cap = DailyCap(limit=1)
    cap.take(MONDAY)
    cap.take(MONDAY)
    assert cap.used == 1


def test_simultaneous_questions_never_exceed_the_limit():
    cap = DailyCap(limit=50)
    with ThreadPoolExecutor(max_workers=16) as pool:
        granted = list(pool.map(lambda _: cap.take(MONDAY), range(200)))
    assert sum(granted) == 50
