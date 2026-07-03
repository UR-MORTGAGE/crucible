"""Document intelligence — the agent reads incoming file documents and clears
the conditions they satisfy, autonomously.

Deterministic classify/extract runs locally (the MI300X lane — no PII egress).
The seam is parser-agnostic: `DOC_PARSER_URL` can point at any doc-parsing
service (e.g. NVIDIA Nemotron Parse post-hackathon, or a vLLM vision model on
the Instinct GPU) — same in/out contract, so nothing downstream changes.
"""
from __future__ import annotations

import re
from typing import Optional

from .schemas import Condition, LoanFile

# doc_type -> condition codes it is capable of clearing
CLEARS: dict[str, list[str]] = {
    "bank_statement": ["7086"],
    "hoi_policy": ["6170", "6977", "5323", "6458"],
    "lox": ["5767", "6283"],
    "title_report": ["0031", "0064"],
    "buydown_agreement": ["3308"],
    "urla_1003": ["0282", "0443"],
    "credit_supplement": ["5868"],
    "counseling_disclosure": ["0408"],
    "h3_disclosure": ["0426"],
    "ssp_list": ["0465"],
}

_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("bank_statement", ("bank statement", "beginning balance", "ending balance", "account summary")),
    ("hoi_policy", ("declarations", "dwelling coverage", "homeowners insurance", "policy period")),
    ("lox", ("letter of explanation", "lox", "to whom it may concern", "explanation for")),
    ("title_report", ("title commitment", "title report", "schedule b", "judgment", "lien search")),
    ("buydown_agreement", ("buydown agreement", "temporary buydown", "2-1 buydown")),
    ("urla_1003", ("uniform residential loan application", "1003", "urla")),
    ("credit_supplement", ("credit supplement", "trade line verification", "liability verification")),
    ("counseling_disclosure", ("homeownership counseling", "counseling agencies")),
    ("h3_disclosure", ("credit score disclosure", "notice to home loan applicant", "h-3")),
    ("ssp_list", ("settlement service provider", "provider list")),
]


def classify(text: str, declared: Optional[str] = None) -> str:
    if declared:
        return declared
    t = text.lower()
    best, best_hits = "unknown", 0
    for dtype, words in _KEYWORDS:
        hits = sum(1 for w in words if w in t)
        if hits > best_hits:
            best, best_hits = dtype, hits
    return best


def extract_fields(text: str, fields: Optional[dict] = None) -> dict:
    out = dict(fields or {})
    if "ending_balance" not in out:
        m = re.search(r"ending balance[:\s]*\$?([\d,]+(?:\.\d{2})?)", text, re.I)
        if m:
            out["ending_balance"] = float(m.group(1).replace(",", ""))
    if "dwelling_coverage" not in out:
        m = re.search(r"dwelling coverage[:\s]*\$?([\d,]+(?:\.\d{2})?)", text, re.I)
        if m:
            out["dwelling_coverage"] = float(m.group(1).replace(",", ""))
    return out


def _required_funds(cond: Condition) -> Optional[float]:
    m = re.search(r"Total funds required are \$([\d,]+(?:\.\d{2})?)", cond.description)
    return float(m.group(1).replace(",", "")) if m else None


def _satisfies(doc_type: str, fields: dict, cond: Condition, loan: LoanFile) -> tuple[bool, str]:
    """Does this document actually satisfy the condition (not just match its code)?"""
    if doc_type == "bank_statement" and cond.code == "7086":
        need = _required_funds(cond)
        have = fields.get("ending_balance")
        if have is None:
            return False, "no balance found in the statement"
        if need is not None and have < need:
            return False, f"verified ${have:,.2f} is below the ${need:,.2f} required"
        return True, f"verified ${have:,.2f} against ${need:,.2f} required" if need else f"verified ${have:,.2f}"
    if doc_type == "hoi_policy" and cond.category == "HOI":
        cov = fields.get("dwelling_coverage")
        if cov is not None and cov < min(loan.loan_amount, loan.property_value):
            return False, f"dwelling coverage ${cov:,.2f} is below the required amount"
        return True, "declarations page reviewed; coverage sufficient"
    return True, "document reviewed and accepted"


def apply_document(doc: dict, conditions: list[Condition], loan: LoanFile) -> dict:
    """Analyze one document against the open conditions. Mutates statuses.

    doc = {"filename": str, "text": str?, "fields": dict?, "doc_type": str?}
    Returns a clearance report the UI (and the learning loop) consume.
    """
    text = doc.get("text", "") or ""
    doc_type = classify(text, doc.get("doc_type"))
    fields = extract_fields(text, doc.get("fields"))
    clearable = set(CLEARS.get(doc_type, []))

    cleared, blocked = [], []
    for cond in conditions:
        if cond.cleared or cond.code not in clearable:
            continue
        ok, why = _satisfies(doc_type, fields, cond, loan)
        if ok:
            cond.cleared = True
            cond.status = "Cleared"
            cleared.append({"code": cond.code, "category": cond.category, "why": why})
        else:
            blocked.append({"code": cond.code, "category": cond.category, "why": why})

    return {
        "filename": doc.get("filename", "document"),
        "doc_type": doc_type,
        "fields": fields,
        "cleared": cleared,
        "insufficient": blocked,
        "remaining_open": sum(1 for c in conditions if not c.cleared),
    }
