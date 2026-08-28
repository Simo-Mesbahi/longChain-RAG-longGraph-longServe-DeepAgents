from ai_course.settings import load_settings


def test_load_settings_uses_defaults(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("MODEL_NAME", raising=False)

    settings = load_settings()

    assert settings.model_provider == "openai"
    assert settings.model_name == "gpt-4.1-mini"
    assert settings.embedding_model == "text-embedding-3-small"


def test_load_settings_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "anthropic")
    monkeypatch.setenv("MODEL_NAME", "example-model")
    monkeypatch.setenv("EMBEDDING_MODEL", "example-embeddings")

    settings = load_settings()

    assert settings.model_provider == "anthropic"
    assert settings.model_name == "example-model"
    assert settings.embedding_model == "example-embeddings"
