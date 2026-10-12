"""Two provider adapters behind a text-in/text-out function."""
import requests

from config import Settings


def generate(settings: Settings, prompt: str) -> str:
    messages = [{"role": "user", "content": prompt}]
    headers = {}
    if settings.provider == "ollama":
        endpoint = settings.base_url + "/api/chat"
        payload = {
            "model": settings.model, "messages": messages,
            "stream": False,
            "options": {"temperature": settings.temperature},
        }
    elif settings.provider == "openrouter":
        endpoint = settings.base_url + "/chat/completions"
        headers["Authorization"] = f"Bearer {settings.api_key}"
        payload = {
            "model": settings.model, "messages": messages,
            "stream": False, "temperature": settings.temperature,
        }
    else:
        raise RuntimeError("Provider chưa có adapter.")

    try:
        response = requests.post(
            endpoint, headers=headers, json=payload,
            timeout=settings.timeout, allow_redirects=False,
        )
    except requests.Timeout:
        raise RuntimeError("Hết thời gian chờ model; kiểm tra dịch vụ và timeout.") from None
    except requests.RequestException:
        raise RuntimeError("Không kết nối được model; kiểm tra mạng và base URL.") from None
    if not 200 <= response.status_code < 300:
        raise RuntimeError(
            f"Dịch vụ trả HTTP {response.status_code}; "
            "kiểm tra endpoint, quyền truy cập, model và hạn mức."
        )
    try:
        data = response.json()
        if isinstance(data, dict) and "error" in data:
            raise RuntimeError("Dịch vụ báo lỗi trong response; không nhận kết quả tóm tắt.")
        if settings.provider == "ollama":
            result = data["message"]["content"]
        else:
            choice = data["choices"][0]
            if isinstance(choice, dict) and (
                choice.get("finish_reason") == "error" or "error" in choice
            ):
                raise RuntimeError("Dịch vụ báo lỗi khi sinh văn bản; kết quả chưa hoàn tất.")
            result = choice["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise RuntimeError("Response không đúng định dạng adapter mong đợi.") from None
    if not isinstance(result, str) or not result.strip():
        raise RuntimeError("Model không trả nội dung văn bản.")
    return result.strip()
