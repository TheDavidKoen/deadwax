import math

import pytest

from deadwax.retrieval.search import top_k, unit


def test_a_unit_vector_has_length_one():
    assert math.hypot(*unit([3.0, 4.0])) == pytest.approx(1.0)


def test_a_zero_vector_cannot_be_normalised():
    with pytest.raises(ValueError):
        unit([0.0, 0.0])


def test_results_are_ranked_by_cosine_similarity():
    vectors = [unit([1.0, 0.0]), unit([0.0, 1.0]), unit([1.0, 1.0])]
    hits = top_k([1.0, 0.1], vectors, k=3)
    assert [hit.position for hit in hits] == [0, 2, 1]


def test_the_query_length_does_not_change_the_ranking():
    vectors = [unit([1.0, 0.0]), unit([0.0, 1.0])]
    long, short = top_k([5.0, 1.0], vectors, k=2), top_k([0.5, 0.1], vectors, k=2)
    assert [hit.position for hit in long] == [hit.position for hit in short]
    assert [hit.score for hit in long] == pytest.approx([hit.score for hit in short])


def test_only_k_results_are_returned():
    vectors = [unit([1.0, float(i)]) for i in range(10)]
    assert len(top_k([1.0, 1.0], vectors, k=3)) == 3
