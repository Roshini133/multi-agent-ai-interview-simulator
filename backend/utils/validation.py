"""Small input-validation helpers."""
import re

from flask import request

from utils.errors import AppError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def json_body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise AppError("invalid_json", "Request body must be a JSON object.", 400)
    return data


def require_str(data: dict, key: str, max_len: int = 255, min_len: int = 1) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not (min_len <= len(value.strip()) <= max_len):
        raise AppError("validation_error", f"'{key}' is required (max {max_len} characters).", 400)
    return value.strip()


def clean_text(text: str, max_len: int) -> str:
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text or "").strip()
    return text[:max_len]
