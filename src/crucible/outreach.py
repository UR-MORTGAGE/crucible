"""Autonomous outreach — the agent works the file like a human underwriter's
processor: for each open condition it decides WHO to contact (broker, title
company, insurance agent, borrower), drafts the message, and dispatches.

Dispatch is real when creds exist (Twilio SMS via TWILIO_ACCOUNT_SID/AUTH_TOKEN/
TWILIO_FROM; voice rides the same seam — AOPE's dialer plugs in here), and an
honest "queued (demo)" otherwise so the demo never fakes a send.
"""
from __future__ import annotations

import os

import httpx

from .schemas import Condition, LoanFile

# category/section -> (role, preferred channel)
_ROUTE: list[tuple[str, str, str]] = [
    ("HOI", "insurance_agent", "email"),
    ("Title", "title_company", "call"),
    ("Disclosure", "broker", "email"),
    ("Assets", "borrower", "sms"),
    ("Credit", "borrower", "sms"),
    ("Borrower", "borrower", "sms"),
    ("TC", "closing_team", "email"),
    ("Property", "trac_team", "email"),
    ("Employment", "broker", "email"),
]

_CONTACT_FIELD = {
    "insurance_agent": "insurance_agent_email",
    "title_company": "title_company_phone",
    "broker": "broker_email",
    "borrower": "borrower_phone",
}


def _route(cond: Condition) -> tuple[str, str]:
    for cat, role, channel in _ROUTE:
        if cond.category == cat:
            return role, channel
    return "broker", "email"


def _draft(cond: Condition, loan: LoanFile, role: str) -> str:
    need = cond.description.split(":", 1)[-1].strip()
    if len(need) > 220:
        need = need[:217] + "…"
    return (f"[{loan.loan_id}] Underwriting condition {cond.code} ({cond.category}): {need} "
            f"Reply to this thread or upload directly to the loan file. — Crucible, autonomous underwriting")


def build_plan(conditions: list[Condition], loan: LoanFile) -> list[dict]:
    """One outreach item per open condition, grouped naturally by contact."""
    plan = []
    for cond in conditions:
        if cond.cleared:
            continue
        role, channel = _route(cond)
        to = getattr(loan, _CONTACT_FIELD.get(role, ""), "") or f"<{role} on file>"
        plan.append({
            "condition_code": cond.code,
            "category": cond.category,
            "contact_role": role,
            "channel": channel,
            "to": to,
            "message": _draft(cond, loan, role),
            "status": "planned",
        })
    return plan


def _twilio_configured() -> bool:
    return bool(os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN") and os.getenv("TWILIO_FROM"))


def _send_sms(to: str, body: str) -> str:
    sid, tok = os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"]
    resp = httpx.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
        auth=(sid, tok),
        data={"From": os.environ["TWILIO_FROM"], "To": to, "Body": body},
        timeout=15,
    )
    resp.raise_for_status()
    return "sent"


def dispatch(plan: list[dict]) -> list[dict]:
    """Execute the plan. Real sends only with real creds + a real destination;
    everything else is queued honestly."""
    live = _twilio_configured()
    for item in plan:
        try:
            if (live and item["channel"] == "sms" and item["to"].startswith("+")):
                item["status"] = _send_sms(item["to"], item["message"])
            else:
                item["status"] = "queued (demo)" if not live else "queued"
        except Exception as e:  # never take the run down over a carrier error
            item["status"] = f"failed: {type(e).__name__}"
    return plan
