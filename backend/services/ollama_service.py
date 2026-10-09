"""Ollama client with retries, timeouts, JSON extraction and validation.

The service never raises raw HTTP errors to callers: everything becomes ``LLMError``
(``LLMUnavailable`` when the server/model cannot be reached), so agents can fall back gracefully.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Iterable

import requests

from utils.logging_config import log_event

log = logging.getLogger(__name__)


class LLMError(Exception):
    """Generic LLM failure (timeout, malformed output, ...)."""


class LLMUnavailable(LLMError):
    """Ollama is not reachable, disabled, or the model is not installed."""


class OllamaService:
    def __init__(self, base_url: str, model: str, timeout: int = 90, retries: int = 2, enabled: bool = True):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.retries = max(0, retries)
        self.enabled = enabled

    @classmethod
    def from_config(cls, cfg) -> "OllamaService":
        return cls(cfg["OLLAMA_BASE_URL"], cfg["OLLAMA_MODEL"], cfg["OLLAMA_TIMEOUT"], cfg["OLLAMA_RETRIES"], cfg["LLM_ENABLED"])

    # ------------------------------------------------------------------ health
    def health(self) -> dict:
        if not self.enabled:
            return {"available": False, "model": self.model, "reason": "LLM disabled by configuration"}
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            r.raise_for_status()
            names = [m.get("name", "") for m in r.json().get("models", [])]
            has_model = self.model in names or f"{self.model}:latest" in names
            return {"available": has_model, "model": self.model, "installed_models": names,
                    "reason": None if has_model else f"Model '{self.model}' is not installed. Run: ollama pull {self.model}"}
        except requests.RequestException:
            return {"available": False, "model": self.model, "reason": f"Ollama is not reachable at {self.base_url}"}

    # -------------------------------------------------------------------- chat
    def chat(self, messages: list[dict], *, json_mode: bool = False, temperature: float = 0.6, max_tokens: int = 400) -> str:
        if not self.enabled:
            raise LLMUnavailable("LLM disabled")
        payload: dict[str, Any] = {
            "model": self.model, "messages": messages, "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if json_mode:
            payload["format"] = "json"
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                r = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
                if r.status_code == 404:
                    raise LLMUnavailable(f"Model '{self.model}' not found. Run: ollama pull {self.model}")
                r.raise_for_status()
                content = (r.json().get("message") or {}).get("content", "").strip()
                if not content:
                    raise LLMError("empty response")
                return content
            except LLMUnavailable:
                raise
            except requests.ConnectionError as e:
                last = LLMUnavailable("Ollama is not reachable")
                log_event(log, "ollama_connection_error", logging.WARNING, attempt=attempt)
            except requests.Timeout as e:
                last = LLMError("Ollama timed out")
                log_event(log, "ollama_timeout", logging.WARNING, attempt=attempt)
            except (requests.RequestException, ValueError, LLMError) as e:
                last = LLMError(f"Ollama error: {type(e).__name__}")
                log_event(log, "ollama_error", logging.WARNING, attempt=attempt, error=type(e).__name__)
            if attempt < self.retries:
                time.sleep(0.4 * (attempt + 1))
        raise last or LLMError("unknown LLM failure")

    def generate_json(self, system: str, user: str, *, required: Iterable[str] = (), temperature: float = 0.4, max_tokens: int = 500) -> dict:
        """Ask for JSON and validate it. Retries once with a repair instruction if malformed."""
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        for attempt in range(2):
            raw = self.chat(messages, json_mode=True, temperature=temperature, max_tokens=max_tokens)
            data = extract_json(raw)
            if isinstance(data, dict) and all(k in data for k in required):
                return data
            log_event(log, "llm_json_invalid", logging.WARNING, attempt=attempt)
            messages = messages + [{"role": "assistant", "content": raw[:800]},
                                   {"role": "user", "content": f"That was not valid. Reply with ONLY a JSON object containing keys: {', '.join(required)}."}]
        raise LLMError("Model returned malformed JSON")


def extract_json(raw: str) -> dict | None:
    """Parse JSON from LLM output, tolerating code fences and surrounding prose."""
    if not raw:
        return None
    text = re.sub(r"```(?:json)?", "", raw).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None
