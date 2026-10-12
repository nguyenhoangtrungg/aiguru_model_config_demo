import os
from dataclasses import FrozenInstanceError

import pytest

from config import ConfigError, load_settings


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in list(os.environ):
        if name.startswith("LLM_"):
            monkeypatch.delenv(name)


@pytest.fixture
def env_file(tmp_path):
    def make(**overrides):
        values = {
            "LLM_PROVIDER": "ollama", "LLM_MODEL": "qwen2.5:7b",
            "LLM_BASE_URL": "http://localhost:11434",
        }
        values.update(overrides)
        path = tmp_path / "config.env"
        path.write_text("\n".join(f"{k}={v}" for k, v in values.items()), encoding="utf-8")
        return path
    return make


def test_defaults_and_frozen(env_file):
    settings = load_settings(env_file())
    assert (settings.temperature, settings.timeout, settings.api_key) == (0.2, 60, "")
    with pytest.raises(FrozenInstanceError):
        settings.model = "different"


@pytest.mark.parametrize("field,value,match", [
    ("LLM_PROVIDER", "", "Thiếu LLM_PROVIDER"),
    ("LLM_PROVIDER", "other", "ollama hoặc openrouter"),
    ("LLM_MODEL", "", "Thiếu LLM_MODEL"),
    ("LLM_MODEL", "replace-with-model", "giá trị mẫu"),
    ("LLM_TEMPERATURE", "", "phải là số"),
    ("LLM_TEMPERATURE", "abc", "phải là số"),
    ("LLM_TEMPERATURE", "NaN", "hữu hạn"),
    ("LLM_TEMPERATURE", "inf", "hữu hạn"),
    ("LLM_TEMPERATURE", "-0.1", "0–1"),
    ("LLM_TEMPERATURE", "1.5", "0–1"),
    ("LLM_TIMEOUT", "0", "lớn hơn 0"),
    ("LLM_TIMEOUT", "-1", "lớn hơn 0"),
    ("LLM_TIMEOUT", "NaN", "hữu hạn"),
    ("LLM_BASE_URL", "", "Thiếu LLM_BASE_URL"),
    ("LLM_BASE_URL", "localhost:11434", "URL HTTP"),
    ("LLM_BASE_URL", "ftp://example.com", "URL HTTP"),
    ("LLM_BASE_URL", "https://user:pass@example.com", "URL HTTP"),
    ("LLM_BASE_URL", "https://example.com?key=secret", "URL HTTP"),
    ("LLM_BASE_URL", "https://example.com/#fragment", "URL HTTP"),
    ("LLM_BASE_URL", "https://example.com:bad", "URL HTTP"),
    ("LLM_BASE_URL", "https://example.com:0", "URL HTTP"),
    ("LLM_BASE_URL", "http://[bad", "URL HTTP"),
])
def test_invalid_values(env_file, field, value, match):
    with pytest.raises(ConfigError, match=match):
        load_settings(env_file(**{field: value}))


def test_cloud_key_hidden(env_file):
    settings = load_settings(env_file(
        LLM_PROVIDER="openrouter", LLM_API_KEY="test-secret",
        LLM_BASE_URL="https://openrouter.ai/api/v1/",
    ))
    assert "test-secret" not in repr(settings)
    assert settings.base_url == "https://openrouter.ai/api/v1"


def test_cloud_missing_key(env_file):
    with pytest.raises(ConfigError, match="LLM_API_KEY"):
        load_settings(env_file(LLM_PROVIDER="openrouter", LLM_BASE_URL="https://openrouter.ai/api/v1"))


def test_cloud_requires_https(env_file):
    with pytest.raises(ConfigError, match="HTTPS"):
        load_settings(env_file(LLM_PROVIDER="openrouter"))


def test_shell_precedence(env_file, monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "shell-model")
    assert load_settings(env_file()).model == "shell-model"


def test_empty_shell_does_not_fall_back(env_file, monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "")
    with pytest.raises(ConfigError, match="LLM_MODEL"):
        load_settings(env_file())


def test_repeated_loads_are_independent(env_file):
    first = load_settings(env_file(LLM_MODEL="first"))
    second = load_settings(env_file(LLM_MODEL="second"))
    assert (first.model, second.model) == ("first", "second")
    assert "LLM_MODEL" not in os.environ


def test_env_only(tmp_path, monkeypatch):
    for key, value in {"LLM_PROVIDER": "ollama", "LLM_MODEL": "local", "LLM_BASE_URL": "http://localhost:11434"}.items():
        monkeypatch.setenv(key, value)
    assert load_settings(tmp_path / "absent.env").model == "local"


def test_no_interpolation(env_file, monkeypatch):
    monkeypatch.setenv("EXTERNAL_MODEL", "injected")
    assert load_settings(env_file(LLM_MODEL="${EXTERNAL_MODEL}")).model == "${EXTERNAL_MODEL}"


def test_secret_not_in_error(env_file):
    with pytest.raises(ConfigError) as exc:
        load_settings(env_file(LLM_PROVIDER="openrouter", LLM_BASE_URL="https://openrouter.ai/api/v1", LLM_API_KEY="secret with spaces"))
    assert "secret with spaces" not in str(exc.value)


@pytest.mark.parametrize("name", ["LLM_TEMPERATURE", "LLM_TIMEOUT", "LLM_API_KEY"])
def test_malformed_env_rejected_without_leaking_values(env_file, name, monkeypatch):
    path = env_file()
    with path.open("a", encoding="utf-8") as stream:
        stream.write(f'\n{name}="private-secret\n')
    monkeypatch.setenv(name, "0.5")
    with pytest.raises(ConfigError, match="sai cú pháp tại dòng") as exc:
        load_settings(path)
    assert "private-secret" not in str(exc.value)


def test_valid_quoted_multiline_env(env_file):
    settings = load_settings(env_file(LLM_MODEL='"quoted-model"', EXTRA='"first\nsecond"'))
    assert settings.model == "quoted-model"
