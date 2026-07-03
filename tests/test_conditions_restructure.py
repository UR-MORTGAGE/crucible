"""Conditions engine, autonomous restructure solver, and the learning loop."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("CRUCIBLE_MODE", "mock")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from crucible.pipeline import run_crucible          # noqa: E402
from crucible.schemas import LoanFile               # noqa: E402
from crucible import restructure, learning          # noqa: E402
from crucible.core import evaluate                   # noqa: E402


def _load(name: str) -> dict:
    return json.loads((ROOT / "data" / "sample_loans" / f"{name}.json").read_text())


def test_conditions_are_generated_and_sectioned():
    r = run_crucible(_load("not_yet"))
    codes = {c.code for c in r.conditions}
    sections = {c.section for c in r.conditions}
    assert r.conditions, "expected a conditions list"
    assert "0282" in codes and "0031" in codes            # 1003 + title, always
    assert "7086" in codes                                 # short funds to close
    assert "Disclosures/Compliance (PTD)" in sections
    assert "TRAC" in sections


def test_restructure_flips_a_denial():
    r = run_crucible(_load("alicia"))               # DTI just over the line
    assert r.decision_state == "not_yet"            # denied as submitted
    assert r.restructure and r.restructure.needed
    assert r.restructure.resulting_state != "not_yet"   # solver found a realistic path
    assert any("buydown" in mv.action.lower() or mv.field == "proposed_housing_payment"
               for mv in r.restructure.moves)


def test_restructure_reports_when_unsavable():
    r = run_crucible(_load("not_yet"))              # Derek — 76.7% DTI, no cheap fix
    assert r.restructure and r.restructure.needed
    assert r.restructure.resulting_state == "not_yet"   # honest: can't be cheaply saved
    assert not r.restructure.moves
    assert "manual" in r.restructure.note.lower()


def test_no_restructure_for_a_clean_file():
    r = run_crucible(_load("easy_yes"))
    assert r.restructure is not None
    assert r.restructure.needed is False
    assert r.decision_state == "fundable_now"


def test_solver_is_pure_and_deterministic():
    loan = LoanFile(**_load("not_yet"))
    a = restructure.solve(loan)
    b = restructure.solve(loan)
    assert [m.model_dump() for m in a.moves] == [m.model_dump() for m in b.moves]


def test_learning_score_orders_files():
    good = LoanFile(**_load("easy_yes"))
    bad = LoanFile(**_load("not_yet"))
    s_good = learning.STORE.score(good, evaluate(good).metrics)
    s_bad = learning.STORE.score(bad, evaluate(bad).metrics)
    assert 0.0 <= s_bad < s_good <= 1.0


def test_approval_score_on_path():
    r = run_crucible(_load("needs_steps"))
    assert 0.0 <= r.approval_score <= 1.0
