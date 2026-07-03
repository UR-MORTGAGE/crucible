"""Cloud lane — Fireworks AI API (OpenAI-compatible) for frontier reasoning."""
from __future__ import annotations

import httpx

from .base import LLMResponse


class FireworksClient:
    name = "cloud"

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.Client(
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    def chat(self, system: str, user: str, **kwargs) -> LLMResponse:
        resp = self._client.post(
            f"{self.base_url}/chat/completions",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": kwargs.get("temperature", 0.3),
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", len(text) // 4)
        return LLMResponse(text=text, tokens=int(tokens))
