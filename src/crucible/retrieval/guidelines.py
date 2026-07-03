"""The local lane's substance: deterministic metric math + a small, citeable
guideline table.

In mock mode this IS the ground truth. Going live, swap `GuidelineRetriever`
for a real RAG retriever over the ingested Fannie/Freddie/FHA/UWM corpus — the
interface (retrieve -> list[Citation]) stays the same, so nothing downstream
changes. Drop the real corpus in ../../data/guidelines/.
"""
from __future__ import annotations

from .. import rag
from ..schemas import Citation, LoanFile, Projected

# --- Program eligibility thresholds, each tied to a citation ---------------
# Illustrative values for the scaffold. Replace quotes/thresholds with the
# exact current guideline text before the demo — Milad validates these.
PROGRAM_RULES: dict[str, dict] = {
    "conventional": {
        "max_dti": 0.50,
        "max_ltv": 0.97,
        "min_credit": 620,
        "min_reserves_months": 2.0,
        "cites": {
            "max_dti": Citation(rule_id="DTI-CONV", source="Fannie Mae Selling Guide B3-6-02",
                                 quote="The maximum allowable DTI ratio is 50%."),
            "max_ltv": Citation(rule_id="LTV-CONV", source="Fannie Mae Eligibility Matrix",
                                 quote="Maximum LTV for a 1-unit principal residence purchase is 97%."),
            "min_credit": Citation(rule_id="FICO-CONV", source="Fannie Mae Selling Guide B3-5.1-01",
                                   quote="The minimum representative credit score is 620."),
            "min_reserves_months": Citation(rule_id="RES-CONV", source="Fannie Mae Selling Guide B3-4.1-01",
                                            quote="Reserves are measured in months of the housing payment."),
        },
    },
    "fha": {
        "max_dti": 0.5699,
        "max_ltv": 0.965,
        "min_credit": 580,
        "min_reserves_months": 0.0,
        "cites": {
            "max_dti": Citation(rule_id="DTI-FHA", source="HUD Handbook 4000.1 II.A.5",
                                quote="Ratios may exceed 43% with documented compensating factors, up to 56.99%."),
            "max_ltv": Citation(rule_id="LTV-FHA", source="HUD Handbook 4000.1 II.A.2",
                                quote="Maximum LTV is 96.5% for borrowers with a minimum decision credit score of 580."),
            "min_credit": Citation(rule_id="FICO-FHA", source="HUD Handbook 4000.1 II.A.1",
                                   quote="A minimum decision credit score of 580 is eligible for maximum financing."),
            "min_reserves_months": Citation(rule_id="RES-FHA", source="HUD Handbook 4000.1 II.A.4",
                                            quote="Reserves are not required for 1-2 unit properties."),
        },
    },
}


_GROUND_QUERIES = {
    "max_dti": "maximum DTI ratio",
    "max_ltv": "maximum LTV purchase",
    "min_credit": "minimum credit score",
    "min_reserves_months": "reserve requirements months",
}


def _sources_compatible(a: str, b: str) -> bool:
    return a.startswith(b) or b.startswith(a)


def _ground_citations() -> int:
    """Replace each citation's quote with the retrieved corpus passage (RAG).

    A quote is only swapped when the retrieved passage's SOURCE matches the
    rule's source — cited-or-silent applies to grounding too. Returns the
    number of citations grounded (0 when the corpus is absent).
    """
    grounded = 0
    for program, rules in PROGRAM_RULES.items():
        prefix = "FHA " if program == "fha" else ""
        for key, cite in rules["cites"].items():
            for hit in rag.retrieve(prefix + _GROUND_QUERIES.get(key, key), k=3):
                if _sources_compatible(hit.source, cite.source):
                    rules["cites"][key] = Citation(
                        rule_id=cite.rule_id, source=cite.source, quote=hit.quote)
                    grounded += 1
                    break
    return grounded


GROUNDED_CITATIONS = _ground_citations()


def grounded_cite(query: str, rule_id: str, fallback: Citation | None = None) -> Citation | None:
    """Retrieve a citation for an arbitrary topic (BK waiting periods, judgments…)."""
    hit = rag.top(query)
    if hit:
        return Citation(rule_id=rule_id, source=hit.source, quote=hit.quote)
    return fallback


def compute_metrics(loan: LoanFile) -> Projected:
    """Real math — this runs locally on the MI300X lane."""
    dti = (loan.monthly_debts + loan.proposed_housing_payment) / loan.monthly_income
    ltv = loan.loan_amount / loan.property_value
    reserves_months = (
        loan.reserves_liquid / loan.proposed_housing_payment
        if loan.proposed_housing_payment else 0.0
    )
    return Projected(
        dti=round(dti, 4),
        ltv=round(ltv, 4),
        reserves_months=round(reserves_months, 2),
    )


class GuidelineRetriever:
    """Returns the citations relevant to a loan. Live: replace with vector RAG."""

    def rules_for(self, program: str) -> dict:
        return PROGRAM_RULES.get(program, PROGRAM_RULES["conventional"])

    def retrieve(self, loan: LoanFile) -> list[Citation]:
        rules = self.rules_for(loan.loan_program)
        return list(rules["cites"].values())
