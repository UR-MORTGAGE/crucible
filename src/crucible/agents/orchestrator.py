"""Wires the adversarial proceeding together and attaches the routing report."""
from __future__ import annotations

from ..clients.base import LLMClient
from ..retrieval.guidelines import GuidelineRetriever, compute_metrics
from ..router import Router
from ..schemas import LoanFile, PathToYes, RestructurePlan
from ..telemetry import RoutingLedger
from .. import conditions as conditions_mod
from .. import restructure as restructure_mod
from ..learning import STORE as LEARN
from .adversary import Adversary
from .advocate import Advocate
from .adjudicator import Adjudicator


class Orchestrator:
    def __init__(self, clients: dict[str, LLMClient], router: Router,
                 ledger: RoutingLedger, retriever: GuidelineRetriever, mode: str) -> None:
        self.clients, self.router, self.ledger, self.retriever, self.mode = (
            clients, router, ledger, retriever, mode)

    def run(self, loan: LoanFile) -> PathToYes:
        # 1. Retrieve guidelines (local RAG) + compute metrics (local math).
        d = self.router.route("retrieve_guidelines")
        self.ledger.record(d.lane, 32)
        citations = self.retriever.retrieve(loan)

        d = self.router.route("compute_metrics")
        self.ledger.record(d.lane, 16)
        metrics = compute_metrics(loan)

        # 2. The proceeding: Adversary -> Advocate -> Adjudicator.
        findings = Adversary(self.clients, self.router, self.ledger, self.mode).scan(loan, metrics, citations)
        remedies = Advocate(self.clients, self.router, self.ledger, self.mode).remedy(loan, metrics, findings, citations)
        path = Adjudicator(self.clients, self.router, self.ledger, self.mode).rule(loan, metrics, findings, remedies, citations)

        # 3. Enrich (conditions, restructure, learned score) + routing story.
        self._enrich(path, loan, metrics, findings)
        path.routing_report = self.ledger.report
        return path

    def _enrich(self, path: PathToYes, loan: LoanFile, metrics, findings) -> None:
        plan = (restructure_mod.solve(loan) if path.decision_state == "not_yet"
                else RestructurePlan(needed=False, resulting_state=path.decision_state, resulting_metrics=metrics))
        path.restructure = plan
        path.conditions = conditions_mod.generate_conditions(loan, metrics, findings, plan)
        path.approval_score = LEARN.score(loan, metrics)
        LEARN.record(loan, metrics, path.decision_state != "not_yet")
        if plan.needed:
            LEARN.record_moves([mv.action for mv in plan.moves], plan.resulting_state != "not_yet")

    def run_events(self, loan: LoanFile):
        """Generator form: yields (event, payload) as the proceeding unfolds, so
        the UI can stream the debate live. Same logic as run(), event by event.
        """
        d = self.router.route("retrieve_guidelines")
        self.ledger.record(d.lane, 32)
        citations = self.retriever.retrieve(loan)

        d = self.router.route("compute_metrics")
        self.ledger.record(d.lane, 16)
        metrics = compute_metrics(loan)
        yield ("opening", {
            "loan_id": loan.loan_id,
            "metrics": metrics.model_dump(),
            "trace": [{"step": "retrieve_guidelines", "lane": "local"},
                      {"step": "compute_metrics", "lane": "local"}],
        })

        findings = Adversary(self.clients, self.router, self.ledger, self.mode).scan(loan, metrics, citations)
        for f in findings:
            yield ("charge", {"finding": f.model_dump(), "lane": "local"})

        remedies = Advocate(self.clients, self.router, self.ledger, self.mode).remedy(loan, metrics, findings, citations)
        rem_by = {r.finding_id: r for r in remedies}
        for f in findings:
            r = rem_by.get(f.id)
            yield ("defense", {"finding_id": f.id, "remedy": (r.model_dump() if r else None), "lane": "cloud"})

        path = Adjudicator(self.clients, self.router, self.ledger, self.mode).rule(loan, metrics, findings, remedies, citations)
        self._enrich(path, loan, metrics, findings)
        path.routing_report = self.ledger.report
        yield ("verdict", {
            "decision_state": path.decision_state,
            "approval_score": path.approval_score,
            "steps": [s.model_dump() for s in path.steps],
            "still_open": [o.model_dump() for o in path.still_open],
            "audit": path.audit.model_dump(),
        })
        yield ("restructure", path.restructure.model_dump() if path.restructure else {"needed": False})
        yield ("conditions", {"items": [c.model_dump() for c in path.conditions],
                              "summary": conditions_mod.section_summary(path.conditions)})
        yield ("routing", path.routing_report.model_dump())
        yield ("done", path.model_dump())
