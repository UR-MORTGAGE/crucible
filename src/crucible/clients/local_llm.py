"""Local lane — an open model served on the MI300X via vLLM (OpenAI-compatible)."""
from __future__ import annotations

import httpx

from .base import LLMResponse


class LocalLLMClient:
    name = "local"

    def __init__(self, base_url: str, model: str, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.Client(timeout=timeout)

    def chat(self, system: str, user: str, **kwargs) -> LLMResponse:
        resp = self._client.post(
            f"{self.base_url}/chat/completions",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": kwargs.get("temperature", 0.2),
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", len(text) // 4)
        return LLMResponse(text=text, tokens=int(tokens))
