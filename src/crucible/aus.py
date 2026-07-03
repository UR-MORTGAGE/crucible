"""AUS integration — Fannie Mae DU / Freddie Mac LPA seam.

Real DU/LPA API access requires approved-technology-provider onboarding, so the
live path activates via env (`DU_API_URL` + `DU_API_KEY`, or `LPA_API_URL`).
Until then, Crucible runs its own evaluator and returns findings in DU-findings
shape, clearly labeled `engine: crucible_simulated` — never passed off as DU.
"""
from __future__ import annotations

import os

import httpx

from .core import evaluate
from .schemas import LoanFile


def build_casefile(loan: LoanFile) -> dict:
    """DU-style casefile payload from a LoanFile (extend per DU spec on onboarding)."""
    return {
        "loanIdentifier": loan.loan_id,
        "mortgageType": loan.loan_program.upper(),
        "propertyUsageType": loan.occupancy,
        "propertyEstimatedValueAmount": loan.property_value,
        "baseLoanAmount": loan.loan_amount,
        "totalMonthlyIncomeAmount": loan.monthly_income,
        "totalMonthlyObligationsAmount": loan.monthly_debts + loan.proposed_housing_payment,
        "creditScoreValue": loan.credit_score,
        "reservesAmount": loan.reserves_liquid,
    }


def submit(loan: LoanFile) -> dict:
    casefile = build_casefile(loan)

    du_url = os.getenv("DU_API_URL")
    if du_url:
        try:
            resp = httpx.post(
                du_url.rstrip("/") + "/casefiles",
                json=casefile,
                headers={"Authorization": f"Bearer {os.getenv('DU_API_KEY', '')}"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return {"engine": "du_api", "recommendation": data.get("recommendation", "Unknown"),
                    "findings": data.get("findings", []), "casefile": casefile}
        except Exception as e:
            return {"engine": "du_api", "error": f"{type(e).__name__}: DU submission failed",
                    "casefile": casefile}

    # Simulated findings — same decision engine the tribunal uses, DU-shaped.
    ev = evaluate(loan)
    if ev.decision_state == "fundable_now":
        rec = "Approve/Eligible"
    elif ev.decision_state == "fundable_with_steps":
        rec = "Approve/Eligible (with conditions)"
    else:
        rec = "Refer/Caution"
    return {
        "engine": "crucible_simulated",
        "recommendation": rec,
        "findings": [f.why_it_fails for f in ev.findings],
        "casefile": casefile,
    }
