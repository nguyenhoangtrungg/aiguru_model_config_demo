from unittest.mock import Mock

import pytest
import requests

from config import Settings
from model_client import generate


def settings(provider="ollama"):
    return Settings(provider, "test-model", 0.2, "https://example.test", "fake-key", 12)


@pytest.mark.parametrize("provider,body,suffix", [
    ("ollama", {"message": {"content": " summary "}}, "/api/chat"),
    ("openrouter", {"choices": [{"message": {"content": " summary "}}]}, "/chat/completions"),
])
def test_adapter_request_response(monkeypatch, provider, body, suffix):
    response = Mock(status_code=200)
    response.json.return_value = body
    post = Mock(return_value=response)
    monkeypatch.setattr(requests, "post", post)
    assert generate(settings(provider), "source") == "summary"
    args, kwargs = post.call_args
    assert args[0] == "https://example.test" + suffix
    assert kwargs["json"]["model"] == "test-model"
    assert kwargs["json"]["messages"] == [{"role": "user", "content": "source"}]
    assert kwargs["json"]["stream"] is False
    assert kwargs["timeout"] == 12 and kwargs["allow_redirects"] is False
    if provider == "ollama":
        assert kwargs["headers"] == {}
        assert kwargs["json"]["options"]["temperature"] == 0.2
    else:
        assert kwargs["headers"]["Authorization"] == "Bearer fake-key"
        assert kwargs["json"]["temperature"] == 0.2


@pytest.mark.parametrize("status", [302, 401, 403, 404, 429, 500])
def test_http_errors_do_not_leak_response(monkeypatch, status):
    response = Mock(status_code=status, text="fake-key")
    monkeypatch.setattr(requests, "post", Mock(return_value=response))
    with pytest.raises(RuntimeError, match=f"HTTP {status}") as exc:
        generate(settings(), "source")
    assert "fake-key" not in str(exc.value)


@pytest.mark.parametrize("error,match", [
    (requests.Timeout("secret"), "Hết thời gian"),
    (requests.ConnectionError("secret"), "Không kết nối"),
])
def test_transport_error(monkeypatch, error, match):
    monkeypatch.setattr(requests, "post", Mock(side_effect=error))
    with pytest.raises(RuntimeError, match=match) as exc:
        generate(settings(), "source")
    assert "secret" not in str(exc.value)


@pytest.mark.parametrize("provider,body", [
    ("ollama", {}), ("ollama", []), ("openrouter", {"choices": []}),
    ("openrouter", {"choices": [None]}),
])
def test_bad_schema(monkeypatch, provider, body):
    response = Mock(status_code=200)
    response.json.return_value = body
    monkeypatch.setattr(requests, "post", Mock(return_value=response))
    with pytest.raises(RuntimeError, match="định dạng"):
        generate(settings(provider), "source")


@pytest.mark.parametrize("content", [None, "", "  ", 42])
def test_empty_or_nontext_response(monkeypatch, content):
    response = Mock(status_code=200)
    response.json.return_value = {"message": {"content": content}}
    monkeypatch.setattr(requests, "post", Mock(return_value=response))
    with pytest.raises(RuntimeError, match="văn bản"):
        generate(settings(), "source")


def test_invalid_json(monkeypatch):
    response = Mock(status_code=200)
    response.json.side_effect = ValueError("private response")
    monkeypatch.setattr(requests, "post", Mock(return_value=response))
    with pytest.raises(RuntimeError, match="định dạng"):
        generate(settings(), "source")
