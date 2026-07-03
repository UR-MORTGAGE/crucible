"""The hybrid token-efficient router — the spine of the whole system.

Policy: keep high-volume, sensitive, and deterministic work on the local MI300X
model; escalate only hard reasoning (and low-confidence local results) to the
Fireworks frontier lane. This is also, on its own, a Track-1 submission.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Lane = Literal["local", "cloud"]

# Default lane per pipeline step. Sensitive/deterministic -> local; hard -> cloud.
STEP_POLICY: dict[str, Lane] = {
    "retrieve_guidelines": "local",   # RAG over the corpus, no PII leaves the box
    "compute_metrics": "local",       # pure math
    "adversary_scan": "local",        # first pass: cheap, high-volume rule matching
    "advocate_synthesis": "cloud",    # creative strategy across products/investors
    "adjudicate": "cloud",            # dialectic resolution + narrative
}


@dataclass(frozen=True)
class RouteDecision:
    lane: Lane
    reason: str


class Router:
    def __init__(self, escalate_threshold: float = 0.7) -> None:
        self.escalate_threshold = escalate_threshold

    def route(self, step: str, *, sensitive: bool = False) -> RouteDecision:
        if sensitive:
            return RouteDecision("local", "sensitive: borrower PII kept on-box")
        lane = STEP_POLICY.get(step, "cloud")
        return RouteDecision(lane, f"policy[{step}] -> {lane}")

    def should_escalate(self, confidence: float) -> bool:
        """A local result below the confidence bar gets re-run on the cloud lane."""
        return confidence < self.escalate_threshold
