"""Autonomous restructuring solver.

If a file can't fund as submitted, search the space of allowable moves —
product switch, larger down payment, debt paydown, seasoned reserves, a temp
buydown, a change-of-circumstance value — and return the minimal-effort set that
flips it to approvable. This is the Advocate, turned into an optimizer.
"""
from __future__ import annotations

import math
from typing import Callable, Optional

from .core import evaluate
from .learning import STORE as LEARN
from .retrieval.guidelines import PROGRAM_RULES
from .schemas import LoanFile, RestructureMove, RestructurePlan

_EFFORT_W = {"low": 1, "medium": 2, "high": 4}
FHA = PROGRAM_RULES["fha"]


def _money(x: float) -> str:
    return f"${x:,.0f}"


def _candidates(loan: LoanFile) -> list[tuple[RestructureMove, Callable[[LoanFile], LoanFile]]]:
    r = PROGRAM_RULES.get(loan.loan_program, PROGRAM_RULES["conventional"])
    out: list[tuple[RestructureMove, Callable[[LoanFile], LoanFile]]] = []

    # 1. Switch to FHA (looser DTI/FICO/reserves) — low borrower effort
    if loan.loan_program == "conventional":
        out.append((
            RestructureMove(action="Switch product to FHA", field="loan_program",
                            from_value="conventional", to_value="fha", effort="low",
                            citation=FHA["cites"]["max_dti"]),
            lambda L: L.model_copy(update={"loan_program": "fha"}),
        ))

    # 2. Larger down payment to clear the LTV cap (change of circumstance)
    ltv = loan.loan_amount / loan.property_value if loan.property_value else 0
    if ltv > r["max_ltv"]:
        target = math.floor(loan.property_value * r["max_ltv"])
        out.append((
            RestructureMove(action="Increase down payment to clear the LTV cap", field="loan_amount",
                            from_value=_money(loan.loan_amount), to_value=_money(target), effort="medium", coc=True,
                            citation=r["cites"]["max_ltv"]),
            lambda L, t=target: L.model_copy(update={"loan_amount": t}),
        ))

    # 3. Reduce loan amount (cash-in) to bring DTI under the cap — scales the payment
    income, debts, housing = loan.monthly_income, loan.monthly_debts, loan.proposed_housing_payment
    dti = (debts + housing) / income if income else 0
    if dti > r["max_dti"] and housing > 0:
        housing_target = max(r["max_dti"] * income - debts, 0)
        factor = housing_target / housing if housing else 0
        if 0 < housing_target < housing and factor >= 0.80:   # cap: <=20% cash-in is realistic
            new_amt = math.floor(loan.loan_amount * factor)
            out.append((
                RestructureMove(action="Reduce loan amount (cash-in) to clear DTI", field="loan_amount",
                                from_value=_money(loan.loan_amount), to_value=_money(new_amt), effort="high", coc=True,
                                citation=r["cites"]["max_dti"]),
                lambda L, a=new_amt, h=housing_target: L.model_copy(update={"loan_amount": a, "proposed_housing_payment": round(h, 2)}),
            ))

    # 4. Pay down revolving debt to clear DTI
    if dti > r["max_dti"]:
        debt_target = max(r["max_dti"] * income - housing, 0)
        if 0 <= debt_target < debts and debt_target >= 0.5 * debts:   # cap: <=50% paydown is realistic
            out.append((
                RestructureMove(action="Pay down revolving debt to clear DTI", field="monthly_debts",
                                from_value=_money(debts), to_value=_money(debt_target), effort="high",
                                citation=r["cites"]["max_dti"]),
                lambda L, d=debt_target: L.model_copy(update={"monthly_debts": round(d, 2)}),
            ))

    # 5. Season reserves to the minimum
    need_months = r["min_reserves_months"]
    have_months = loan.reserves_liquid / housing if housing else 0
    if have_months < need_months:
        target_res = math.ceil(need_months * housing)
        out.append((
            RestructureMove(action="Season reserves to the minimum", field="reserves_liquid",
                            from_value=_money(loan.reserves_liquid), to_value=_money(target_res), effort="low",
                            citation=r["cites"]["min_reserves_months"]),
            lambda L, t=target_res: L.model_copy(update={"reserves_liquid": t}),
        ))

    # 6. Temporary buydown to lower the qualifying payment (~12% year-1)
    if dti > r["max_dti"] and housing > 0:
        new_housing = round(housing * 0.88, 2)
        out.append((
            RestructureMove(action="Add a 2-1 temporary buydown (lowers qualifying payment)", field="proposed_housing_payment",
                            from_value=_money(housing), to_value=_money(new_housing), effort="low"),
            lambda L, h=new_housing: L.model_copy(update={"proposed_housing_payment": h, "has_temp_buydown": True}),
        ))

    return out


def solve(loan: LoanFile, max_moves: int = 2) -> RestructurePlan:
    base = evaluate(loan)
    if base.decision_state != "not_yet":
        return RestructurePlan(needed=False, resulting_state=base.decision_state,
                               resulting_metrics=base.metrics, note="Fundable as submitted — no restructure required.")

    cands = _candidates(loan)
    combos: list[list] = [[c] for c in cands]
    if max_moves >= 2:
        for i, a in enumerate(cands):
            for b in cands[i + 1:]:
                combos.append([a, b])

    best: Optional[tuple] = None
    for combo in combos:
        trial = loan
        for _, fn in combo:
            trial = fn(trial)
        res = evaluate(trial)
        if res.decision_state != "not_yet":
            eff = sum(_EFFORT_W[mv.effort] for mv, _ in combo)
            bonus = 0 if res.decision_state == "fundable_now" else 1
            # learned tie-break: among equal-effort plans, prefer the moves
            # that have historically converted (the loop learning.py feeds)
            learned = sum(LEARN.move_success_rate(mv.action) for mv, _ in combo) / len(combo)
            key = (eff + bonus, len(combo), -learned)
            if best is None or key < best[0]:
                best = (key, [mv for mv, _ in combo], trial, res)

    if best is None:
        return RestructurePlan(needed=True, resulting_state="not_yet",
                               note="No one- or two-move restructure clears this file; manual structuring required.")

    _, moves, trial, res = best
    return RestructurePlan(needed=True, moves=moves, resulting_state=res.decision_state,
                           resulting_metrics=res.metrics,
                           note=f"{len(moves)}-move restructure clears underwriting → {res.decision_state.replace('_', ' ')}.")
