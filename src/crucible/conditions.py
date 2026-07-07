"""Underwriting conditions engine.

Turns a loan file (+ findings + any restructure) into a real, categorized
conditions list — the actual output an underwriter produces. Sections, codes,
and language mirror a UWM conditions report (Master / TRAC / Underwriter II
(PTD) / Disclosures-Compliance (PTD) / Underwriter To Obtain And Clear).

Codes here map to the standard UWM condition catalog. In production the catalog
and the exact wording come from the LOS; the triggers stay the same.
"""
from __future__ import annotations

from typing import Optional

from .schemas import Condition, Finding, LoanFile, Projected, RestructurePlan

SECTION_ORDER = [
    "Master", "TRAC", "Underwriter II (PTD)",
    "Disclosures/Compliance (PTD)", "Underwriter To Obtain And Clear",
]


def _funds_to_close(loan: LoanFile) -> tuple[float, float, float]:
    if loan.funds_to_close and loan.funds_to_close > 0:
        total = loan.funds_to_close
    else:
        # A down payment is owed on purchases only — a refi's funds to close
        # are closing costs (equity is not cash the borrower must bring).
        down = max(loan.property_value - loan.loan_amount, 0) if loan.loan_purpose == "purchase" else 0.0
        closing = 0.03 * loan.loan_amount
        total = round(down + closing, 2)
    verified = loan.reserves_liquid
    return total, verified, max(round(total - verified, 2), 0)


def generate_conditions(loan: LoanFile, m: Projected, findings: list[Finding],
                        restructure: Optional[RestructurePlan] = None) -> list[Condition]:
    conds: list[Condition] = []

    def add(code, section, category, description, prior_to="docs"):
        conds.append(Condition(code=code, section=section, category=category,
                               description=description, prior_to=prior_to))

    purchase = loan.loan_purpose == "purchase"

    # ---- Master ----
    add("0973", "Master", "Property",
        "Property: Appraisal Waiver accepted. No appraisal currently needed as long as the Appraisal Waiver remains approved.")
    if loan.has_temp_buydown:
        add("3308", "Master", "TC",
            "TC: Temporary Buydown Agreement to be executed by all parties and returned in the closing package.")
    if loan.loan_purpose == "refi_rate_term" and loan.cash_out_amount > 500:
        add("0562", "Master", "Credit",
            f"Credit: A restructure of this loan is required due to excessive cash back (${loan.cash_out_amount:,.2f}) on a rate and term refinance. "
            "Provide documentation and/or submit a Change of Circumstance in EASE to resolve the restructure.")

    # ---- TRAC ----
    add("0031", "TRAC", "Title", "Title (TRAC/TRAC+): TRAC Curative Team to obtain clear title.")
    if loan.open_judgment_amount > 0:
        desc = loan.open_judgment_desc or "the judgment"
        add("0064", "TRAC", "Title",
            f"Title (TRAC+): Broker to verify if {desc} in the original amount of "
            f"${loan.open_judgment_amount:,.2f}, if not already released, will need to be paid in full or subordinated.")
        add("0064", "TRAC", "Title",
            f"Title (TRAC+): TRAC Curative Team to obtain payoff for {desc} in the original amount of "
            f"${loan.open_judgment_amount:,.2f} lien on title.")
    if loan.loan_program == "conventional":
        add("7015", "TRAC", "Property",
            "Property (Conv): TRAC Team to provide UWM-approved title summary with chain of title, legal description, and verification of current property taxes.")

    # ---- Underwriter II (PTD) ----
    total, verified, short = _funds_to_close(loan)
    if short > 0:
        add("7086", "Underwriter II (PTD)", "Assets",
            "Assets: Short funds to close and/or reserves. Document sufficient funds for the closing of this transaction. "
            f"Total funds required are ${total:,.2f}. This must be verified by the most recent 1 month bank statement. ${verified:,.2f} currently verified.")
    if loan.credit_inquiries > 0:
        add("5767", "Underwriter II (PTD)", "Credit",
            "Credit: Letter of explanation from borrower(s) for credit inquiries. The explanation must reference each inquiry specifically "
            "and state whether any new credit was obtained as a result.")
    for lia in loan.missing_liabilities:
        add("5868", "Underwriter II (PTD)", "Credit",
            f"Credit: Liability(s) missing from the credit report. Provide acceptable documentation to support the balance and payment for: {lia}.")
    if purchase:
        add("6170", "Underwriter II (PTD)", "HOI",
            "HOI: Provide an updated homeowners insurance declarations page reflecting the insurer, a 12-month term, a deductible no more than 5% "
            "of dwelling coverage, dwelling coverage covering the lower of replacement cost or loan amount, at least one borrower as insured, and the correct property address.")
    else:
        add("6977", "Underwriter II (PTD)", "HOI",
            "HOI Refi Renewal: Provide an updated renewal homeowners insurance declarations page reflecting the insurer, a 12-month term, a deductible "
            "no more than 5% of dwelling coverage, sufficient dwelling coverage, at least one borrower as insured, and the correct property address.")
        add("6283", "Underwriter II (PTD)", "Borrower",
            "Borrower: The terms of the loan must reflect a tangible benefit to the applicant. Provide a signed and dated letter of explanation "
            "from the borrower describing the tangible benefit of the loan.")

    # ---- Disclosures/Compliance (PTD) ----
    add("0282", "Disclosures/Compliance (PTD)", "Disclosure",
        "Disclosure: 1003 — fully executed initial 1003 with the correct subject property address, signed and dated by all borrower(s) and the loan originator.")
    add("0408", "Disclosures/Compliance (PTD)", "Disclosure",
        "Disclosure: Homeownership Counseling Disclosure listing 10 counseling agencies near the borrower's current mailing address, dated within 3 days of the earliest 1003 signature date.")
    add("0426", "Disclosures/Compliance (PTD)", "Disclosure",
        "Disclosure: H-3 model disclosure (credit score, date, score range, how the score compares to others, key factors, and Notice to Home Loan Applicant).")
    add("0465", "Disclosures/Compliance (PTD)", "Disclosure",
        "Disclosure: Settlement Service Provider List with company name, phone, and address matching the service types in Block C of the LE, dated within 3 days of the application date.")
    if loan.state.upper() == "TN":
        add("0443", "Disclosures/Compliance (PTD)", "Disclosure",
            "Disclosure: TN — the state license number held by the MLO and the MLO's company must be disclosed on the 1003.")

    # ---- Underwriter To Obtain And Clear ----
    add("0299", "Underwriter To Obtain And Clear", "Employment",
        "Employment: Verbal verification of employment for each borrower to be completed within 10 business days prior to the Note date.",
        prior_to="funding")

    # COCs the restructure requires
    if restructure and restructure.needed:
        for mv in restructure.moves:
            if mv.coc:
                add("0571", "Underwriter To Obtain And Clear", "Credit",
                    f"Credit: Underwriter to approve the change of circumstance requested for {mv.field} From: {mv.from_value} To: {mv.to_value}.")

    conds.sort(key=lambda c: SECTION_ORDER.index(c.section) if c.section in SECTION_ORDER else 99)
    return conds


def section_summary(conds: list[Condition]) -> list[dict]:
    """[{section, count}] in report order — for the UI's section headers."""
    counts: dict[str, int] = {}
    for c in conds:
        counts[c.section] = counts.get(c.section, 0) + 1
    return [{"section": s, "count": counts[s]} for s in SECTION_ORDER if s in counts]
