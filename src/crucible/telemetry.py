"""Routing ledger — records every model call so the UI can show the router
working: how much stayed local on the MI300X vs. escalated to Fireworks, and
what that cost. This is the token-efficiency story, made visible.
"""
from __future__ import annotations

from .schemas import RoutingReport

# Rough per-token cost. Local inference on owned/credited GPU is ~free at the
# margin; the cloud lane is what you pay for. Tune with real numbers on Day 1.
PRICE_PER_TOKEN = {"local": 0.0, "cloud": 0.0000009}


class RoutingLedger:
    def __init__(self) -> None:
        self.report = RoutingReport()

    def record(self, lane: str, tokens: int, *, escalated: bool = False) -> None:
        if lane == "local":
            self.report.local_calls += 1
        else:
            self.report.cloud_calls += 1
        self.report.tokens += tokens
        self.report.est_cost_usd = round(
            self.report.est_cost_usd + tokens * PRICE_PER_TOKEN.get(lane, 0.0), 6
        )
        if escalated:
            self.report.escalations += 1

    @property
    def local_share(self) -> float:
        total = self.report.local_calls + self.report.cloud_calls
        return (self.report.local_calls / total) if total else 0.0
