"""Pure, fast underwriting evaluator — no LLM calls.

This is the deterministic heart the agents narrate and the restructure solver
searches against. Given a LoanFile it returns findings (grounded + cited),
remedies, a decision, and the metrics. Same rules as the agent mock path.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .retrieval.guidelines import PROGRAM_RULES, compute_metrics, grounded_cite
from .schemas import Finding, LoanFile, Projected, Remedy

FHA = PROGRAM_RULES["fha"]

_ADVERSE = {
    "F-DTI": "Debt-to-income ratio exceeds program maximums.",
    "F-LTV": "Loan-to-value exceeds the maximum for the requested program.",
    "F-FICO": "Credit score does not meet the minimum required.",
    "F-RES": "Insufficient cash reserves after closing.",
    "F-BK": "Insufficient time elapsed since bankruptcy discharge.",
    "F-FC": "Insufficient time elapsed since foreclosure completion.",
    "F-JUDG": "Unsatisfied judgment or lien against the borrower or property.",
}


@dataclass
class Evaluation:
    metrics: Projected
    findings: list[Finding]
    remedies: dict[str, Remedy]
    decision_state: str
    addressable: list[str] = field(default_factory=list)
    open_ids: list[str] = field(default_factory=list)


def find(loan: LoanFile, m: Projected) -> list[Finding]:
    r = PROGRAM_RULES.get(loan.loan_program, PROGRAM_RULES["conventional"])
    c = r["cites"]
    out: list[Finding] = []
    if m.dti is not None and m.dti > r["max_dti"]:
        out.append(Finding(id="F-DTI", rule_id=c["max_dti"].rule_id, field_in_file="monthly_debts + proposed_housing_payment",
                           why_it_fails=f"DTI {m.dti:.1%} exceeds the {r['max_dti']:.0%} maximum for {loan.loan_program}.",
                           severity="fatal" if m.dti > r["max_dti"] + .10 else "high", citation=c["max_dti"]))
    if m.ltv is not None and m.ltv > r["max_ltv"]:
        out.append(Finding(id="F-LTV", rule_id=c["max_ltv"].rule_id, field_in_file="loan_amount / property_value",
                           why_it_fails=f"LTV {m.ltv:.1%} exceeds the {r['max_ltv']:.1%} maximum for {loan.loan_program}.",
                           severity="high", citation=c["max_ltv"]))
    if loan.credit_score < r["min_credit"]:
        out.append(Finding(id="F-FICO", rule_id=c["min_credit"].rule_id, field_in_file="credit_score",
                           why_it_fails=f"Credit score {loan.credit_score} is below the {r['min_credit']} minimum for {loan.loan_program}.",
                           severity="fatal" if loan.credit_score < r["min_credit"] - 40 else "high", citation=c["min_credit"]))
    if m.reserves_months is not None and m.reserves_months < r["min_reserves_months"]:
        out.append(Finding(id="F-RES", rule_id=c["min_reserves_months"].rule_id, field_in_file="reserves_liquid",
                           why_it_fails=f"Reserves {m.reserves_months:.1f} mo are below the {r['min_reserves_months']:.0f}-mo minimum for {loan.loan_program}.",
                           severity="medium", citation=c["min_reserves_months"]))

    # Credit events — citations retrieved from the corpus (RAG), not a table.
    if loan.months_since_chapter7 is not None and loan.months_since_chapter7 < 48:
        out.append(Finding(id="F-BK", rule_id="BK-CH7", field_in_file="months_since_chapter7",
                           why_it_fails=(f"Only {loan.months_since_chapter7} months since Chapter 7 discharge; "
                                         "48 months are required absent documented extenuating circumstances."),
                           severity="fatal" if loan.months_since_chapter7 < 24 else "high",
                           citation=grounded_cite("chapter 7 bankruptcy waiting period", "BK-CH7")))
    if loan.months_since_foreclosure is not None and loan.months_since_foreclosure < 84:
        out.append(Finding(id="F-FC", rule_id="FC-WAIT", field_in_file="months_since_foreclosure",
                           why_it_fails=(f"Only {loan.months_since_foreclosure} months since foreclosure; "
                                         "84 months are required."),
                           severity="high",
                           citation=grounded_cite("foreclosure waiting period", "FC-WAIT")))
    if loan.open_judgment_amount > 0:
        desc = loan.open_judgment_desc or "an open judgment"
        out.append(Finding(id="F-JUDG", rule_id="JUDG-LIEN", field_in_file="open_judgment_amount",
                           why_it_fails=(f"{desc} in the amount of ${loan.open_judgment_amount:,.2f} "
                                         "must be paid in full or subordinated prior to or at closing."),
                           severity="medium",
                           citation=grounded_cite("judgments liens paid in full subordinated", "JUDG-LIEN")))
    return out


def _remedy(loan: LoanFile, m: Projected, f: Finding) -> Remedy:
    conv = loan.loan_program == "conventional"
    if f.id == "F-DTI":
        if conv and m.dti is not None and m.dti <= FHA["max_dti"]:
            return Remedy(finding_id=f.id, remedy_type="product_switch", effort="low", citation=FHA["cites"]["max_dti"],
                         action="Switch to FHA, which allows a higher DTI with compensating factors.",
                         projected_effect=f"DTI {m.dti:.1%} within FHA's {FHA['max_dti']:.2%} ceiling.")
        return Remedy(finding_id=f.id, remedy_type="borrower_action", effort="high", citation=f.citation,
                     action="Pay down revolving debt to bring DTI under the program maximum.", projected_effect="Reduces qualifying DTI below the ceiling.")
    if f.id == "F-LTV":
        return Remedy(finding_id=f.id, remedy_type="borrower_action", effort="medium", citation=f.citation,
                     action="Increase the down payment to lower LTV under the cap.", projected_effect="Brings LTV to or below the maximum.")
    if f.id == "F-FICO":
        if conv and loan.credit_score >= FHA["min_credit"]:
            return Remedy(finding_id=f.id, remedy_type="product_switch", effort="low", citation=FHA["cites"]["min_credit"],
                         action="Switch to FHA, whose minimum decision credit score is lower.", projected_effect=f"Score {loan.credit_score} meets FHA's {FHA['min_credit']} minimum.")
        return Remedy(finding_id=f.id, remedy_type="borrower_action", effort="high", citation=f.citation,
                     action="Rapid-rescore after paying down utilization / disputing errors.", projected_effect="Raises the representative score above the minimum.")
    if f.id == "F-RES":
        if conv:
            return Remedy(finding_id=f.id, remedy_type="product_switch", effort="low", citation=FHA["cites"]["min_reserves_months"],
                         action="Switch to FHA, which requires no reserves for 1-2 unit properties.", projected_effect="Reserve shortfall no longer applies.")
        return Remedy(finding_id=f.id, remedy_type="borrower_action", effort="low", citation=f.citation,
                     action="Season additional liquid reserves to meet the minimum.", projected_effect="Reserves reach the minimum.")
    if f.id == "F-JUDG":
        return Remedy(finding_id=f.id, remedy_type="borrower_action", effort="medium", citation=f.citation,
                     action="Pay the judgment in full or record a subordination agreement prior to or at closing.",
                     projected_effect="Clears the title impediment; TRAC obtains payoff or subordination.")
    if f.id in ("F-BK", "F-FC"):
        return Remedy(finding_id=f.id, remedy_type="borrower_action", effort="high", citation=f.citation,
                     action="Document extenuating circumstances, or wait out the remaining seasoning period.",
                     projected_effect="Meets the credit-event waiting requirement.")
    return Remedy(finding_id=f.id, remedy_type="borrower_action", effort="medium", citation=f.citation,
                 action="Provide additional documentation for manual review.", projected_effect="Enables reconsideration.")


def evaluate(loan: LoanFile) -> Evaluation:
    m = compute_metrics(loan)
    findings = find(loan, m)
    remedies = {f.id: _remedy(loan, m, f) for f in findings}
    addressable, open_ids = [], []
    for f in findings:
        r = remedies[f.id]
        (addressable if r.effort in ("low", "medium") else open_ids).append(f.id)
    state = "fundable_now" if not findings else ("not_yet" if open_ids else "fundable_with_steps")
    return Evaluation(m, findings, remedies, state, addressable, open_ids)
