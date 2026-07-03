"""Named borrower personas for the demo. Real stories beat "CR-2002" — they make
the stakes legible to a judge in three seconds.
"""
from __future__ import annotations

SCENARIOS: list[dict] = [
    {
        "key": "maria", "name": "Maria Delgado", "initials": "MD",
        "story": "Self-employed designer, 2 yrs of 1099 income, excellent credit.",
        "expected": "fundable_now",
        "loan": {"loan_id": "MARIA-01", "loan_program": "conventional", "occupancy": "primary",
                 "property_value": 500000, "loan_amount": 400000, "monthly_income": 12000,
                 "monthly_debts": 1500, "proposed_housing_payment": 2200,
                 "credit_score": 760, "reserves_liquid": 20000},
    },
    {
        "key": "james", "name": "James Okafor", "initials": "JO",
        "story": "W-2 nurse. A new car loan pushed his DTI just over the line.",
        "expected": "fundable_with_steps",
        "loan": {"loan_id": "JAMES-01", "loan_program": "conventional", "occupancy": "primary",
                 "property_value": 400000, "loan_amount": 380000, "monthly_income": 8000,
                 "monthly_debts": 1800, "proposed_housing_payment": 2600,
                 "credit_score": 700, "reserves_liquid": 5000},
    },
    {
        "key": "nguyen", "name": "The Nguyen Family", "initials": "NG",
        "story": "First-time buyers, 3% down, thin post-close reserves.",
        "expected": "fundable_with_steps",
        "loan": {"loan_id": "NGUYEN-01", "loan_program": "conventional", "occupancy": "primary",
                 "property_value": 350000, "loan_amount": 341000, "monthly_income": 9000,
                 "monthly_debts": 900, "proposed_housing_payment": 2500,
                 "credit_score": 720, "reserves_liquid": 2000},
    },
    {
        "key": "alicia", "name": "Alicia Reyes", "initials": "AR",
        "story": "DTI just over the FHA line — a temporary buydown rescues it.",
        "expected": "not_yet",
        "loan": {"loan_id": "ALICIA-01", "loan_program": "conventional", "occupancy": "primary",
                 "property_value": 500000, "loan_amount": 400000, "monthly_income": 8000,
                 "monthly_debts": 1000, "proposed_housing_payment": 3640,
                 "credit_score": 720, "reserves_liquid": 12000},
    },
    {
        "key": "derek", "name": "Derek Cole", "initials": "DC",
        "story": "Credit dinged after a divorce; income tight against the payment.",
        "expected": "not_yet",
        "loan": {"loan_id": "DEREK-01", "loan_program": "conventional", "occupancy": "primary",
                 "property_value": 300000, "loan_amount": 294000, "monthly_income": 6000,
                 "monthly_debts": 2200, "proposed_housing_payment": 2400,
                 "credit_score": 580, "reserves_liquid": 0},
    },
]
