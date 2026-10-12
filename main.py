"""Run from this directory: python main.py --env-file .env.local."""
import argparse
from pathlib import Path

from config import ConfigError, load_settings
from model_client import generate

ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Tóm tắt với cấu hình model riêng.")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--check-config", action="store_true")
    args = parser.parse_args()
    env_file = args.env_file
    if env_file is not None and not env_file.is_file():
        print("Lỗi cấu hình: file được chỉ định không tồn tại hoặc không phải file.")
        return 2
    if env_file is None:
        env_file = ROOT / ".env"
    try:
        settings = load_settings(env_file)
    except ConfigError as exc:
        print(f"Lỗi cấu hình: {exc}")
        return 2
    except (OSError, UnicodeError):
        print("Lỗi cấu hình: không đọc được file môi trường UTF-8.")
        return 2
    print(
        f"provider={settings.provider} | model={settings.model}\n"
        f"temperature={settings.temperature} | timeout={settings.timeout}s"
    )
    if args.check_config:
        print("Cấu hình hợp lệ về mặt cục bộ; chưa gọi API.")
        return 0
    try:
        source = (ROOT / "samples" / "source.txt").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        print("Lỗi dữ liệu: không đọc được samples/source.txt dạng UTF-8.")
        return 2
    if not source.strip():
        print("Lỗi dữ liệu: samples/source.txt đang rỗng.")
        return 2
    prompt = f"Tóm tắt văn bản sau thành 3 ý chính bằng tiếng Việt:\n\n{source}"
    try:
        print(generate(settings, prompt))
    except RuntimeError as exc:
        print(f"Lỗi gọi model: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
