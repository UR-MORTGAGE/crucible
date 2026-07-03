"""Adjudicator — rules on the cited record and assembles the Path to Yes.

A finding is *addressable* when it has a low/medium-effort, guideline-valid
remedy -> it becomes a ranked step. Otherwise it stays OPEN with a plain-language,
Reg-B-style adverse-action reason. Any claim without a citation is flagged
unverified, never guessed.
"""
from __future__ import annotations

from ..clients.base import LLMClient
from ..router import Router
from ..schemas import (Audit, Citation, DecisionState, Finding, LoanFile, OpenIssue,
                       PathStep, PathToYes, Projected, Remedy)
from ..telemetry import RoutingLedger
from .prompts import ADJUDICATOR

from ..core import _ADVERSE  # single source of truth for Reg-B reason language


class Adjudicator:
    def __init__(self, clients: dict[str, LLMClient], router: Router, ledger: RoutingLedger, mode: str) -> None:
        self.clients, self.router, self.ledger, self.mode = clients, router, ledger, mode

    def rule(self, loan: LoanFile, metrics: Projected, findings: list[Finding],
             remedies: list[Remedy], citations: list[Citation]) -> PathToYes:
        decision = self.router.route("adjudicate")
        resp = self.clients[decision.lane].chat(ADJUDICATOR, f"LOAN {loan.loan_id}")
        self.ledger.record(decision.lane, resp.tokens, escalated=(decision.lane == "cloud"))

        remedy_by = {r.finding_id: r for r in remedies}
        steps: list[PathStep] = []
        still_open: list[OpenIssue] = []
        unverified: list[str] = []
        rank = 1

        for f in findings:
            if f.citation is None:
                unverified.append(f.id)
            r = remedy_by.get(f.id)
            if r and r.effort in ("low", "medium") and r.citation is not None:
                steps.append(PathStep(
                    rank=rank, action=r.action, why=f.why_it_fails,
                    projected=Projected(dti=metrics.dti, ltv=metrics.ltv, reserves_months=metrics.reserves_months),
                    investor="FHA" if r.remedy_type == "product_switch" else None,
                    effort=r.effort, citation=r.citation))
                rank += 1
            else:
                still_open.append(OpenIssue(
                    issue=f.why_it_fails,
                    adverse_action_reason=_ADVERSE.get(f.id, "Does not meet program eligibility."),
                    citation=f.citation))

        decision_state: DecisionState = (
            "fundable_now" if not findings
            else "not_yet" if still_open
            else "fundable_with_steps"
        )

        return PathToYes(
            loan_id=loan.loan_id,
            decision_state=decision_state,
            metrics=metrics,
            steps=steps,
            still_open=still_open,
            audit=Audit(
                every_claim_has_citation=not unverified,
                unverified_flags=unverified,
            ),
        )
