"""Top-level entrypoint: a loan dict in, a PathToYes out."""
from __future__ import annotations

from typing import Optional

from .clients import build_clients
from .config import load_config
from .agents.orchestrator import Orchestrator
from .retrieval.guidelines import GuidelineRetriever
from .router import Router
from .schemas import LoanFile, PathToYes
from .telemetry import RoutingLedger


def run_crucible(loan_dict: dict, mode: Optional[str] = None) -> PathToYes:
    cfg = load_config()
    mode = (mode or cfg.mode).lower()

    loan = LoanFile(**loan_dict)
    ledger = RoutingLedger()
    router = Router(cfg.escalate_threshold)
    clients = build_clients(cfg if mode == cfg.mode else _with_mode(cfg, mode))
    retriever = GuidelineRetriever()

    return Orchestrator(clients, router, ledger, retriever, mode).run(loan)


def iter_crucible_events(loan_dict: dict, mode: Optional[str] = None):
    """Streaming form of run_crucible: yields (event, payload) tuples."""
    cfg = load_config()
    mode = (mode or cfg.mode).lower()

    loan = LoanFile(**loan_dict)
    ledger = RoutingLedger()
    router = Router(cfg.escalate_threshold)
    clients = build_clients(cfg if mode == cfg.mode else _with_mode(cfg, mode))
    retriever = GuidelineRetriever()

    yield from Orchestrator(clients, router, ledger, retriever, mode).run_events(loan)


def _with_mode(cfg, mode: str):
    from dataclasses import replace
    return replace(cfg, mode=mode)
