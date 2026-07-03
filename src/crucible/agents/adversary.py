"""Adversary — tries to kill the loan. Every finding is grounded in real math
against a cited threshold. The numbers are deterministic (local lane); an LLM
only enriches the narrative on the live path — it never invents a threshold.
"""
from __future__ import annotations

from ..clients.base import LLMClient
from ..core import find as core_find
from ..router import Router
from ..schemas import Citation, Finding, LoanFile, Projected
from ..telemetry import RoutingLedger
from .prompts import ADVERSARY


class Adversary:
    def __init__(self, clients: dict[str, LLMClient], router: Router, ledger: RoutingLedger, mode: str) -> None:
        self.clients, self.router, self.ledger, self.mode = clients, router, ledger, mode

    def scan(self, loan: LoanFile, metrics: Projected, citations: list[Citation]) -> list[Finding]:
        # Borrower data is sensitive -> the router pins this pass to the local box.
        decision = self.router.route("adversary_scan", sensitive=True)
        resp = self.clients[decision.lane].chat(ADVERSARY, self._payload(loan, metrics))
        self.ledger.record(decision.lane, resp.tokens)
        # Grounded findings come from the deterministic core engine (single
        # source of truth). Live TODO: merge LLM-authored narrative from resp.text.
        return core_find(loan, metrics)

    @staticmethod
    def _payload(loan: LoanFile, metrics: Projected) -> str:
        return (f"LOAN {loan.loan_id} program={loan.loan_program} | "
                f"DTI={metrics.dti} LTV={metrics.ltv} FICO={loan.credit_score} "
                f"reserves_mo={metrics.reserves_months}")
