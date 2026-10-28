import json

from deadwax.agent.models import DEFAULT_EMBEDDING_MODEL, EMBEDDING_DIMENSIONS
from deadwax.retrieval.chunking import chunk_documents
from deadwax.retrieval.index import INDEX_FILE, read_index

DOCUMENTS_FILE = INDEX_FILE.parent / "documents.json"
ARTISTS_FILE = INDEX_FILE.parent / "artists.json"

INDEX = read_index()
DOCUMENTS = json.loads(DOCUMENTS_FILE.read_text(encoding="utf-8"))


def test_the_index_was_built_with_the_configured_embedding_model():
    assert (INDEX.model, INDEX.dimensions) == (DEFAULT_EMBEDDING_MODEL, EMBEDDING_DIMENSIONS)


def test_the_index_is_up_to_date_with_the_documents():
    expected = chunk_documents(DOCUMENTS)
    assert [c.id for c in INDEX.chunks] == [c.id for c in expected]
    assert [c.text for c in INDEX.chunks] == [c.text for c in expected]


def test_every_vector_has_the_configured_size():
    assert {len(vector) for vector in INDEX.vectors} == {EMBEDDING_DIMENSIONS}


def test_every_chunk_carries_a_source_and_licence_for_citation():
    assert all(chunk.source.startswith("https://") for chunk in INDEX.chunks)
    assert {chunk.licence for chunk in INDEX.chunks} == {"CC0 1.0", "CC BY-SA 4.0"}


def test_every_library_artist_was_reviewed_by_a_person():
    artists = json.loads(ARTISTS_FILE.read_text(encoding="utf-8"))
    assert all(entry["reviewed"] for entry in artists.values())
    assert set(artists) == set(DOCUMENTS)
