from deadwax.agent import embeddings


class FakeEmbedder:
    def __init__(self):
        self.calls = []
        self.pauses = []

    def embed_documents(self, texts, task_type):
        self.calls.append((list(texts), task_type))
        return [[float(len(text)), 1.0] for text in texts]


def install(monkeypatch, tmp_path):
    fake = FakeEmbedder()
    monkeypatch.setattr(embeddings, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(embeddings, "build_embeddings", lambda: fake)
    monkeypatch.setattr(embeddings.time, "sleep", fake.pauses.append)
    return fake


def test_documents_are_embedded_once_and_then_served_from_the_cache(monkeypatch, tmp_path):
    fake = install(monkeypatch, tmp_path)
    first = embeddings.embed_documents(["a", "bb"])
    second = embeddings.embed_documents(["a", "bb"])
    assert first == second == [[1.0, 1.0], [2.0, 1.0]]
    assert len(fake.calls) == 1


def test_only_texts_missing_from_the_cache_are_sent(monkeypatch, tmp_path):
    fake = install(monkeypatch, tmp_path)
    embeddings.embed_documents(["a"])
    embeddings.embed_documents(["a", "new"])
    assert fake.calls[-1] == (["new"], embeddings.DOCUMENT)


def test_queries_and_documents_are_embedded_for_different_tasks(monkeypatch, tmp_path):
    fake = install(monkeypatch, tmp_path)
    embeddings.embed_documents(["same text"])
    embeddings.embed_query("same text")
    assert [task for _, task in fake.calls] == [embeddings.DOCUMENT, embeddings.QUERY]


def test_a_large_request_is_sent_in_batches(monkeypatch, tmp_path):
    fake = install(monkeypatch, tmp_path)
    embeddings.embed_documents([f"text {i}" for i in range(embeddings.BATCH_SIZE + 1)])
    assert [len(texts) for texts, _ in fake.calls] == [embeddings.BATCH_SIZE, 1]


def test_batches_are_paced_to_stay_under_the_per_minute_quota(monkeypatch, tmp_path):
    fake = install(monkeypatch, tmp_path)
    embeddings.embed_documents([f"text {i}" for i in range(embeddings.BATCH_SIZE * 3)])
    expected = embeddings.BATCH_SIZE * 60 / embeddings.TEXTS_PER_MINUTE
    assert fake.pauses == [expected, expected]


def test_a_single_batch_is_not_delayed(monkeypatch, tmp_path):
    fake = install(monkeypatch, tmp_path)
    embeddings.embed_query("what year did Can form?")
    assert fake.pauses == []
