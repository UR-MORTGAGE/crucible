"""Advocate — for each kill-shot, finds the strongest guideline-valid path around it."""
from __future__ import annotations

from ..clients.base import LLMClient
from ..core import _remedy as core_remedy
from ..router import Router
from ..schemas import Citation, Finding, LoanFile, Projected, Remedy
from ..telemetry import RoutingLedger
from .prompts import ADVOCATE


class Advocate:
    def __init__(self, clients: dict[str, LLMClient], router: Router, ledger: RoutingLedger, mode: str) -> None:
        self.clients, self.router, self.ledger, self.mode = clients, router, ledger, mode

    def remedy(self, loan: LoanFile, metrics: Projected, findings: list[Finding],
               citations: list[Citation]) -> list[Remedy]:
        # Creative cross-product strategy -> the router escalates this to the cloud lane.
        decision = self.router.route("advocate_synthesis")
        resp = self.clients[decision.lane].chat(ADVOCATE, self._payload(loan, findings))
        self.ledger.record(decision.lane, resp.tokens, escalated=(decision.lane == "cloud"))
        # Remedies come from the deterministic core engine (single source of truth).
        return [core_remedy(loan, metrics, f) for f in findings]

    @staticmethod
    def _payload(loan: LoanFile, findings: list[Finding]) -> str:
        return f"LOAN {loan.loan_id} findings=" + ", ".join(f.id for f in findings)
