from deadwax.agent import tracing


def without_credentials(monkeypatch):
    for name in tracing.CREDENTIALS:
        monkeypatch.delenv(name, raising=False)


def test_tracing_is_disabled_without_credentials(monkeypatch):
    without_credentials(monkeypatch)
    assert tracing.enabled() is False


def test_a_run_without_credentials_yields_no_callbacks(monkeypatch):
    without_credentials(monkeypatch)
    with tracing.traced("test") as trace:
        assert trace.callbacks == []
        assert trace.id is None
        assert trace.url is None


def test_scores_without_a_trace_id_are_dropped(monkeypatch):
    without_credentials(monkeypatch)
    tracing.record_scores(None, {"answer": True})
    tracing.flush()


def test_one_missing_credential_disables_tracing(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    assert tracing.enabled() is False
