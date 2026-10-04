"""A caching wrapper around the Anthropic client, so reruns are free and reproducible.

Modes
  replay  answer only from eval/cache/llm.jsonl; a request that is not cached raises CacheMiss (the metric is then
          reported as "not run", never invented)
  record  answer from the cache when possible, otherwise call the API (needs ANTHROPIC_API_KEY) and append the response
  off     no model at all
The cache key is a hash of the whole request (model, system prompt, messages, parameters), so changing a prompt
invalidates exactly the answers it affects.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

from eval.common import CACHE

CACHE_FILE = CACHE / "llm.jsonl"


class CacheMiss(RuntimeError):
    """A model response was needed that is not in the cache and live calls are not allowed."""


class ModelUnavailable(RuntimeError):
    """The run asked for a model but the mode is `off`, or record mode has no key."""


def request_key(kwargs: dict[str, Any]) -> str:
    keep = {k: kwargs.get(k) for k in ("model", "system", "messages", "max_tokens", "thinking", "output_config", "temperature")}
    return hashlib.sha256(json.dumps(keep, sort_keys=True, default=str).encode()).hexdigest()


class CachedLLM:
    """Quacks like `anthropic.Anthropic()` for the one call the project makes: `client.messages.create(...)`."""

    def __init__(self, mode: str = "replay", path: Path = CACHE_FILE, live_client: Optional[Any] = None) -> None:
        if mode not in ("replay", "record", "off"):
            raise ValueError(f"unknown LLM mode {mode!r}")
        self.mode = mode
        self.path = path
        self._live = live_client
        self._entries: dict[str, str] = {}
        self.hits = self.misses = self.calls = 0
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    self._entries[row["key"]] = row["text"]
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **kwargs: Any) -> Any:
        if self.mode == "off":
            raise ModelUnavailable("LLM mode is off")
        key = request_key(kwargs)
        if key in self._entries:
            self.hits += 1
            return self._response(self._entries[key])
        if self.mode == "replay":
            self.misses += 1
            raise CacheMiss("this request is not in the response cache")
        client = self._live or self._make_live()
        response = client.messages.create(**kwargs)
        text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
        self.calls += 1
        self._entries[key] = text
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"key": key, "model": kwargs.get("model"), "text": text}, ensure_ascii=False) + "\n")
        return self._response(text)

    def _make_live(self) -> Any:
        key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("POWERPILOT_ANTHROPIC_API_KEY")
        if not key:
            raise ModelUnavailable("record mode needs ANTHROPIC_API_KEY (or POWERPILOT_ANTHROPIC_API_KEY)")
        from app.core.config import Settings
        from app.intelligence.llm.llm_copilot import make_anthropic_client

        client = make_anthropic_client(Settings(anthropic_api_key=key))
        if client is None:
            raise ModelUnavailable("the anthropic package is not available")
        self._live = client
        return client

    @staticmethod
    def _response(text: str) -> Any:
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason="end_turn")
