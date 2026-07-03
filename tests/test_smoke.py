"""Offline smoke tests — no GPU, no network. Verifies the pipeline runs in mock
mode and the three sample loans land in their expected states.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("CRUCIBLE_MODE", "mock")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from crucible.pipeline import run_crucible  # noqa: E402


def _load(name: str) -> dict:
    return json.loads((ROOT / "data" / "sample_loans" / f"{name}.json").read_text())


def test_easy_yes_is_fundable_now():
    r = run_crucible(_load("easy_yes"))
    assert r.decision_state == "fundable_now"
    assert not r.still_open
    assert r.audit.every_claim_has_citation


def test_needs_steps_has_a_path():
    r = run_crucible(_load("needs_steps"))
    assert r.decision_state == "fundable_with_steps"
    assert r.steps and not r.still_open
    assert all(s.citation is not None for s in r.steps)


def test_not_yet_has_open_issue_with_reason():
    r = run_crucible(_load("not_yet"))
    assert r.decision_state == "not_yet"
    assert r.still_open
    assert all(o.adverse_action_reason for o in r.still_open)


def test_routing_report_is_populated():
    r = run_crucible(_load("needs_steps"))
    assert r.routing_report.local_calls >= 1
    assert r.routing_report.cloud_calls >= 1
