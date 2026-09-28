"""Minimal client for the local Ollama server (HTTP on localhost, standard library only).

The model only sees what the harness puts in `messages`; it cannot read files or call tools.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable

from .config import Config


class LLMError(Exception):
    pass


@dataclass
class ChatResult:
    text: str
    model: str
    stats: dict = field(default_factory=dict)


class LocalGemma:
    def __init__(self, cfg: Config, mode: str = "local"):
        if mode != "local":
            raise LLMError(
                f"Execution mode '{mode}' is not configured. This project runs Gemma locally "
                "(--mode local, the default); no online endpoint is set up."
            )
        m = cfg.model
        self.host = m["host"].rstrip("/")
        self.model = m["name"]
        self.num_ctx = m["num_ctx"]
        self.think = m.get("think", False)
        self.timeout = m.get("timeout_s", 300)
        self.temps = m.get("temperature", {})
        self.identifier = m.get("identifier", self.model)

    # --- server checks -------------------------------------------------------------
    def _get(self, path: str, timeout: float = 3) -> dict:
        with urllib.request.urlopen(self.host + path, timeout=timeout) as r:
            return json.load(r)

    def runtime_version(self) -> str | None:
        try:
            return self._get("/api/version").get("version")
        except Exception:
            return None

    def check(self) -> None:
        """Raise a helpful LLMError if the server is down or the model is missing."""
        try:
            tags = self._get("/api/tags")
        except (urllib.error.URLError, OSError):
            raise LLMError(
                f"Cannot reach the local Ollama server at {self.host}.\n"
                "  Start it in another terminal with:  ollama serve\n"
                "  (search mode works without the model: wiki search \"...\")"
            )
        names = {t["name"].split(":")[0] for t in tags.get("models", [])}
        if self.model.split(":")[0] not in names:
            raise LLMError(
                f"Model '{self.model}' is not installed in Ollama.\n"
                "  See README > Setup > 'Create the local model' (ollama create gemma4-e2b-qat -f Modelfile)."
            )

    def loaded_models(self) -> list[dict]:
        try:
            return self._get("/api/ps").get("models", [])
        except Exception:
            return []

    # --- generation ----------------------------------------------------------------
    def chat(
        self,
        messages: list[dict],
        *,
        purpose: str = "chat",
        schema: dict | None = None,
        on_token: Callable[[str], None] | None = None,
        num_predict: int | None = None,
    ) -> ChatResult:
        body: dict = {
            "model": self.model,
            "messages": messages,
            "stream": on_token is not None,
            "think": self.think,
            "keep_alive": "10m",
            "options": {"temperature": self.temps.get(purpose, 0.2), "num_ctx": self.num_ctx},
        }
        if num_predict:
            body["options"]["num_predict"] = num_predict
        if schema is not None:
            body["format"] = schema  # Ollama structured output: constrains decoding to this JSON schema
        req = urllib.request.Request(
            self.host + "/api/chat",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                if on_token is None:
                    final = json.load(r)
                    text = final.get("message", {}).get("content", "")
                else:
                    parts = []
                    final = {}
                    for line in r:
                        if not line.strip():
                            continue
                        chunk = json.loads(line)
                        if "error" in chunk:
                            raise LLMError(chunk["error"])
                        piece = chunk.get("message", {}).get("content", "")
                        if piece:
                            parts.append(piece)
                            on_token(piece)
                        if chunk.get("done"):
                            final = chunk
                    text = "".join(parts)
        except urllib.error.HTTPError as e:
            raise LLMError(f"Ollama returned HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")
        except (urllib.error.URLError, OSError) as e:
            self.check()  # turns connection problems into a readable message
            raise LLMError(f"Model call failed: {e}")
        wall = time.perf_counter() - t0
        ns = 1e9
        stats = {
            "wall_s": round(wall, 2),
            "load_s": round(final.get("load_duration", 0) / ns, 2),
            "prompt_tokens": final.get("prompt_eval_count"),
            "prompt_s": round(final.get("prompt_eval_duration", 0) / ns, 2),
            "output_tokens": final.get("eval_count"),
            "output_s": round(final.get("eval_duration", 0) / ns, 2),
        }
        if stats["output_tokens"] and final.get("eval_duration"):
            stats["tokens_per_s"] = round(stats["output_tokens"] / (final["eval_duration"] / ns), 1)
        return ChatResult(text=text.strip(), model=self.model, stats=stats)

    def chat_json(self, messages: list[dict], schema: dict, *, purpose: str, retries: int = 1) -> tuple[dict, ChatResult]:
        last_err = None
        for _ in range(retries + 1):
            res = self.chat(messages, purpose=purpose, schema=schema)
            try:
                return json.loads(res.text), res
            except json.JSONDecodeError as e:
                last_err = e
        raise LLMError(f"Model did not return valid JSON: {last_err}")
