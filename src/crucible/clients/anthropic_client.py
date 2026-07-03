"""Cloud lane via the Anthropic API — Claude Fable 5 for the hard reasoning.

Fable 5 specifics (per the Anthropic API): thinking is always on, so the
`thinking` parameter is omitted; depth is controlled with `output_config.effort`.
Refusal fallbacks to Opus 4.8 are opted in by default. The `anthropic` import is
lazy so the package works without the SDK installed.
"""
from __future__ import annotations

import os

from .base import LLMResponse


class AnthropicClient:
    name = "cloud"

    def __init__(self, model: str = "claude-fable-5", effort: str = "high") -> None:
        from anthropic import Anthropic  # lazy: only needed when provider=anthropic
        self._client = Anthropic()  # reads ANTHROPIC_API_KEY / ant profile
        self.model = model
        self.effort = effort

    def chat(self, system: str, user: str, **kwargs) -> LLMResponse:
        resp = self._client.beta.messages.create(
            model=self.model,
            max_tokens=kwargs.get("max_tokens", 2048),
            system=system,
            output_config={"effort": kwargs.get("effort", self.effort)},
            betas=["server-side-fallback-2026-06-01"],
            fallbacks=[{"model": "claude-opus-4-8"}],
            messages=[{"role": "user", "content": user}],
        )
        if resp.stop_reason == "refusal":
            return LLMResponse(text="", tokens=0)
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        u = resp.usage
        tokens = int((getattr(u, "input_tokens", 0) or 0) + (getattr(u, "output_tokens", 0) or 0))
        return LLMResponse(text=text, tokens=tokens)
