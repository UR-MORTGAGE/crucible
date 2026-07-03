"""Client interface. Every lane exposes the same `chat()` so agents don't care
which model answered — the Router decides that.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class LLMResponse:
    text: str
    tokens: int


@runtime_checkable
class LLMClient(Protocol):
    name: str
    def chat(self, system: str, user: str, **kwargs) -> LLMResponse: ...


class MockClient:
    """Offline stub. Agents supply their own deterministic content in mock mode;
    this just stands in so the call graph (and the routing ledger) is real.
    """
    def __init__(self, name: str) -> None:
        self.name = name

    def chat(self, system: str, user: str, **kwargs) -> LLMResponse:
        approx = (len(system) + len(user)) // 4  # ~4 chars/token
        return LLMResponse(text="", tokens=max(approx, 1))
