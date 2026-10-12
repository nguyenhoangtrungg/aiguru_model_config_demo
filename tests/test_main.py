import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

import main


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    for key in list(os.environ):
        if key.startswith("LLM_"):
            monkeypatch.delenv(key)


def test_check_config_never_calls_model(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["main.py", "--env-file", str(main.ROOT / ".env.example"), "--check-config"])
    call = Mock(side_effect=AssertionError("Must not call model"))
    monkeypatch.setattr(main, "generate", call)
    assert main.main() == 0
    call.assert_not_called()
    assert "chưa gọi API" in capsys.readouterr().out


def test_missing_variable_stops_before_model(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["main.py", "--env-file", str(main.ROOT / "profiles/missing-model.env.example")])
    call = Mock(side_effect=AssertionError("Must not call model"))
    monkeypatch.setattr(main, "generate", call)
    assert main.main() == 2
    call.assert_not_called()
    assert "Thiếu LLM_MODEL" in capsys.readouterr().out


def test_missing_explicit_file(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["main.py", "--env-file", str(tmp_path / "absent.env")])
    assert main.main() == 2


def test_main_uses_sample_and_handles_runtime_error(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["main.py", "--env-file", str(main.ROOT / ".env.example")])
    call = Mock(side_effect=RuntimeError("HTTP 401"))
    monkeypatch.setattr(main, "generate", call)
    assert main.main() == 1
    assert "30 câu hỏi" in call.call_args.args[1]
    assert "HTTP 401" in capsys.readouterr().out


def test_default_env_is_next_to_script(monkeypatch, tmp_path, capsys):
    (tmp_path / ".env").write_text("LLM_PROVIDER=ollama\nLLM_MODEL=beside-script\nLLM_BASE_URL=http://localhost:11434\n")
    monkeypatch.setattr(main, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["main.py", "--check-config"])
    assert main.main() == 0
    assert "beside-script" in capsys.readouterr().out
