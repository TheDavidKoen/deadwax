import math

import pytest

from deadwax.retrieval.chunking import Chunk
from deadwax.retrieval.index import read_index, write_index

CHUNKS = [
    Chunk("can-facts", "Can", "MusicBrainz", "Can is a group.", "mb", "CC0 1.0"),
    Chunk("can-01", "Can", "Introduction", "Can — Introduction\nKöln.", "wp", "CC BY-SA 4.0"),
]


def test_an_index_round_trips_through_its_file(tmp_path):
    path = tmp_path / "index.jsonl"
    write_index(path, CHUNKS, [[3.0, 4.0], [1.0, 0.0]], "model-x", 2, "2026-10-28")
    index = read_index(path)
    assert (index.model, index.dimensions, index.built) == ("model-x", 2, "2026-10-28")
    assert index.chunks == tuple(CHUNKS)


def test_stored_vectors_are_normalised(tmp_path):
    path = tmp_path / "index.jsonl"
    write_index(path, CHUNKS, [[3.0, 4.0], [1.0, 0.0]], "model-x", 2, "2026-10-28")
    assert all(math.hypot(*v) == pytest.approx(1.0) for v in read_index(path).vectors)


def test_one_chunk_per_line_keeps_diffs_readable(tmp_path):
    path = tmp_path / "index.jsonl"
    write_index(path, CHUNKS, [[3.0, 4.0], [1.0, 0.0]], "model-x", 2, "2026-10-28")
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1 + len(CHUNKS)


def test_a_vector_of_the_wrong_size_is_refused(tmp_path):
    with pytest.raises(ValueError, match="dimensions"):
        write_index(tmp_path / "i.jsonl", CHUNKS, [[1.0, 0.0], [1.0]], "m", 2, "d")


def test_a_count_mismatch_is_refused(tmp_path):
    with pytest.raises(ValueError, match="vectors"):
        write_index(tmp_path / "i.jsonl", CHUNKS, [[1.0, 0.0]], "m", 2, "d")
