"""Typed contracts for Crucible. The `PathToYes` object is the deliverable —
the auditable thing the borrower keeps.
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field

Severity = Literal["low", "medium", "high", "fatal"]
Effort = Literal["low", "medium", "high"]
DecisionState = Literal["fundable_now", "fundable_with_steps", "not_yet"]
RemedyType = Literal["compensating_factor", "product_switch", "investor_overlay", "borrower_action"]


class Citation(BaseModel):
    """A grounded reference. Nothing is asserted without one — cited or silent."""
    rule_id: str
    source: str
    quote: str


class LoanFile(BaseModel):
    """A borrower's file. Extra fields are allowed so real exports drop in cleanly."""
    model_config = {"extra": "allow"}

    loan_id: str
    loan_program: str = "conventional"          # conventional | fha | va | usda
    occupancy: str = "primary"
    property_value: float
    loan_amount: float
    monthly_income: float                        # gross qualifying income / month
    monthly_debts: float                         # existing obligations, excl. new housing
    proposed_housing_payment: float              # PITI of the subject property
    credit_score: int
    reserves_liquid: float                       # liquid post-close reserves, dollars
    # optional context — drives conditions; safe defaults keep old files valid
    loan_purpose: str = "purchase"               # purchase | refi_rate_term | refi_cash_out
    cash_out_amount: float = 0.0
    has_temp_buydown: bool = False
    state: str = "TN"
    funds_to_close: float = 0.0                  # 0 => estimate from down payment + costs
    credit_inquiries: int = 1
    missing_liabilities: list[str] = Field(default_factory=list)
    # credit events — None/0 means "not present on the file"
    months_since_chapter7: Optional[int] = None
    months_since_foreclosure: Optional[int] = None
    open_judgment_amount: float = 0.0
    open_judgment_desc: str = ""
    # contacts for autonomous outreach (any may be blank in demo)
    broker_email: str = ""
    borrower_phone: str = ""
    title_company_phone: str = ""
    insurance_agent_email: str = ""


class Finding(BaseModel):
    id: str
    rule_id: str
    field_in_file: str
    why_it_fails: str
    severity: Severity
    citation: Optional[Citation] = None


class Remedy(BaseModel):
    finding_id: str
    remedy_type: RemedyType
    action: str
    projected_effect: str
    effort: Effort
    citation: Optional[Citation] = None


class Projected(BaseModel):
    dti: Optional[float] = None
    ltv: Optional[float] = None
    reserves_months: Optional[float] = None


class PathStep(BaseModel):
    rank: int
    action: str
    why: str
    projected: Projected = Field(default_factory=Projected)
    investor: Optional[str] = None
    effort: Effort = "medium"
    citation: Optional[Citation] = None


class OpenIssue(BaseModel):
    issue: str
    adverse_action_reason: str                   # Reg-B-style, plain language
    citation: Optional[Citation] = None


class RoutingReport(BaseModel):
    local_calls: int = 0
    cloud_calls: int = 0
    tokens: int = 0
    est_cost_usd: float = 0.0
    escalations: int = 0


class Audit(BaseModel):
    every_claim_has_citation: bool = True
    unverified_flags: list[str] = Field(default_factory=list)


class Condition(BaseModel):
    code: str
    section: str            # Master / TRAC / Underwriter II (PTD) / ...
    category: str           # Credit / Assets / HOI / Title / Disclosure / Property / TC / Borrower
    description: str
    status: str = "Not Cleared"
    cleared: bool = False
    prior_to: str = "docs"  # docs (PTD) | funding (PTF) | closing


class RestructureMove(BaseModel):
    action: str
    field: str
    from_value: str
    to_value: str
    effort: Effort = "medium"
    coc: bool = False       # triggers a change-of-circumstance condition
    citation: Optional[Citation] = None


class RestructurePlan(BaseModel):
    needed: bool = False
    moves: list[RestructureMove] = Field(default_factory=list)
    resulting_state: DecisionState = "not_yet"
    resulting_metrics: Projected = Field(default_factory=Projected)
    note: str = ""


class PathToYes(BaseModel):
    loan_id: str
    decision_state: DecisionState
    metrics: Projected = Field(default_factory=Projected)
    approval_score: float = 0.0
    steps: list[PathStep] = Field(default_factory=list)
    still_open: list[OpenIssue] = Field(default_factory=list)
    conditions: list[Condition] = Field(default_factory=list)
    restructure: Optional[RestructurePlan] = None
    routing_report: RoutingReport = Field(default_factory=RoutingReport)
    audit: Audit = Field(default_factory=Audit)
