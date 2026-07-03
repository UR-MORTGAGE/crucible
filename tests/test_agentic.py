"""The agentic underwriter: RAG-grounded citations, expanded findings,
document intelligence, autonomous outreach, AUS seam, and the learning loop.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("CRUCIBLE_MODE", "mock")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient           # noqa: E402

import crucible.server as server                     # noqa: E402
from crucible import rag                             # noqa: E402
from crucible.retrieval.guidelines import PROGRAM_RULES, GROUNDED_CITATIONS  # noqa: E402
from crucible.pipeline import run_crucible           # noqa: E402

client = TestClient(server.app)


def _loan(name: str) -> dict:
    return json.loads((ROOT / "data" / "sample_loans" / f"{name}.json").read_text())


# ---- RAG grounding -----------------------------------------------------------
def test_corpus_is_indexed():
    assert rag.corpus_size() >= 10


def test_citations_are_grounded_in_corpus():
    assert GROUNDED_CITATIONS >= 6            # most table cites re-grounded via retrieval
    q = PROGRAM_RULES["conventional"]["cites"]["max_dti"].quote
    assert "50%" in q                          # quote text now comes from the corpus passage


def test_guideline_search_endpoint():
    r = client.get("/guidelines/search", params={"q": "chapter 7 bankruptcy waiting period"}).json()
    assert r["hits"] and "B3-5.1" in r["hits"][0]["source"]
    assert "4 years" in r["hits"][0]["quote"] or "48 months" in r["hits"][0]["quote"]


# ---- expanded underwriting dimensions -----------------------------------------
def test_bankruptcy_seasoning_blocks():
    loan = {**_loan("easy_yes"), "loan_id": "BK-TEST", "months_since_chapter7": 20}
    r = run_crucible(loan)
    assert r.decision_state == "not_yet"
    assert any("bankruptcy" in o.adverse_action_reason.lower() for o in r.still_open)


def test_judgment_creates_title_conditions_and_step():
    loan = {**_loan("easy_yes"), "loan_id": "JUDG-TEST",
            "open_judgment_amount": 7192.00,
            "open_judgment_desc": "Small Claims Judgment in favor of Discover Bank"}
    r = run_crucible(loan)
    assert r.decision_state == "fundable_with_steps"          # judgment is addressable
    assert any("subordinat" in s.action.lower() or "pay the judgment" in s.action.lower() for s in r.steps)
    codes = [c.code for c in r.conditions]
    assert codes.count("0064") == 2                            # verify + payoff, like the real report


# ---- the agentic workfile loop -------------------------------------------------
def test_document_intelligence_clears_conditions():
    loan = _loan("needs_steps")
    client.post("/underwrite", json={"loan": loan})
    lid = loan["loan_id"]

    # bank statement with sufficient funds clears 7086
    rep = client.post(f"/workfile/{lid}/documents", json={
        "filename": "boa_june.pdf",
        "text": "Bank Statement — Account Summary. Beginning balance $31,000. Ending balance: $41,250.00",
    }).json()
    assert rep["doc_type"] == "bank_statement"
    assert any(c["code"] == "7086" for c in rep["cleared"])

    # HOI declarations page clears the HOI condition
    rep2 = client.post(f"/workfile/{lid}/documents", json={
        "filename": "hoi_dec.pdf",
        "text": "Homeowners Insurance Declarations. Policy period 12 months. Dwelling coverage: $400,000.00",
    }).json()
    assert rep2["cleared"], rep2
    assert rep2["remaining_open"] < rep["remaining_open"]


def test_insufficient_document_does_not_clear():
    loan = {**_loan("needs_steps"), "loan_id": "SHORTFUNDS-1"}
    client.post("/underwrite", json={"loan": loan})
    rep = client.post("/workfile/SHORTFUNDS-1/documents", json={
        "filename": "small.pdf",
        "text": "Bank Statement. Ending balance: $900.00",
    }).json()
    assert not rep["cleared"]
    assert any(c["code"] == "7086" for c in rep["insufficient"])


def test_outreach_plans_every_open_condition():
    loan = _loan("not_yet")
    client.post("/underwrite", json={"loan": loan})
    r = client.post(f"/workfile/{loan['loan_id']}/outreach").json()
    assert r["items"]
    roles = {i["contact_role"] for i in r["items"]}
    assert "title_company" in roles or "broker" in roles
    assert all(i["status"].startswith("queued") for i in r["items"])   # honest demo mode
    assert all(i["condition_code"] in i["message"] for i in r["items"])


def test_aus_seam_returns_du_shaped_findings():
    for name, expected in [("needs_steps", "Approve/Eligible"), ("not_yet", "Refer/Caution")]:
        loan = {**_loan(name), "loan_id": f"AUS-{name}"}
        client.post("/underwrite", json={"loan": loan})
        r = client.post(f"/workfile/AUS-{name}/aus").json()
        assert r["engine"] == "crucible_simulated"
        assert r["recommendation"].startswith(expected)
        assert r["casefile"]["loanIdentifier"] == f"AUS-{name}"


def test_learning_accumulates():
    r = client.get("/learning").json()
    assert r["files_underwritten"] > 0
    assert r["condition_clearances"].get("7086", {}).get("count", 0) >= 1
