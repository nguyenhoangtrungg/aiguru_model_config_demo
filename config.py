"""Load one explicit env file, then let process variables take precedence."""
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    provider: str
    model: str
    temperature: float
    base_url: str
    api_key: str = field(repr=False)
    timeout: float


def load_settings(env_file: Path) -> Settings:
    # No interpolation: each value is literal. Do not mutate os.environ.
    file_values = (
        dotenv_values(env_file, interpolate=False)
        if env_file.is_file() else {}
    )
    values = {**file_values, **os.environ}

    def required(name: str) -> str:
        value = (values.get(name) or "").strip()
        if not value:
            raise ConfigError(f"Thiếu {name}: hãy đặt biến này trước khi chạy.")
        if any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ConfigError(f"{name} không được chứa ký tự điều khiển.")
        return value

    def number(name: str, default: str) -> float:
        try:
            value = float(values.get(name, default))
        except (TypeError, ValueError):
            raise ConfigError(f"{name} phải là số.") from None
        if not math.isfinite(value):
            raise ConfigError(f"{name} phải là số hữu hạn.")
        return value

    provider = required("LLM_PROVIDER").lower()
    if provider not in {"ollama", "openrouter"}:
        raise ConfigError("LLM_PROVIDER phải là ollama hoặc openrouter.")

    model = required("LLM_MODEL")
    if model.startswith("replace-with-"):
        raise ConfigError("LLM_MODEL còn là giá trị mẫu; hãy điền model thật.")
    temperature = number("LLM_TEMPERATURE", "0.2")
    if not 0 <= temperature <= 1:
        raise ConfigError("LLM_TEMPERATURE phải nằm trong khoảng 0–1.")
    timeout = number("LLM_TIMEOUT", "60")
    if timeout <= 0:
        raise ConfigError("LLM_TIMEOUT phải lớn hơn 0.")

    base_url = required("LLM_BASE_URL").rstrip("/")
    try:
        url = urlsplit(base_url)
        port = url.port
        valid = (
            url.scheme in {"http", "https"}
            and bool(url.hostname)
            and url.username is None and url.password is None
            and not url.query and not url.fragment
            and not any(c.isspace() for c in base_url)
            and (port is None or port > 0)
        )
    except ValueError:
        valid = False
    if not valid:
        raise ConfigError(
            "LLM_BASE_URL phải là URL HTTP(S), không chứa "
            "thông tin đăng nhập, query hoặc fragment."
        )
    if provider == "openrouter" and url.scheme != "https":
        raise ConfigError("OpenRouter cần LLM_BASE_URL dùng HTTPS.")

    api_key = required("LLM_API_KEY") if provider == "openrouter" else ""
    if api_key and (not api_key.isascii() or any(c.isspace() for c in api_key)):
        raise ConfigError("LLM_API_KEY phải là chuỗi ASCII không chứa khoảng trắng.")
    return Settings(provider, model, temperature, base_url, api_key, timeout)
