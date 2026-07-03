"""Salesforce connector — pulls loan files from the underwrite LWC's Opportunity.

Config-driven. When SF creds are present it queries the org over SOQL and maps
Opportunity fields to a Crucible LoanFile via FIELD_MAP. With no creds it reports
`configured() == False` and the server falls back to the demo personas — so the
UI always works, and flips to real data the moment the org is wired.

Env:
  SF_USERNAME, SF_PASSWORD, SF_SECURITY_TOKEN, SF_DOMAIN (login|test)
Adjust FIELD_MAP and SOQL_FIELDS to your org's API names.
"""
from __future__ import annotations

import os
from typing import Optional

# SF Opportunity (and related) API field name  ->  Crucible LoanFile field.
# These are placeholders — set them to your underwrite LWC's real field names.
FIELD_MAP: dict[str, str] = {
    "Loan_Number__c": "loan_id",
    "Loan_Program__c": "loan_program",
    "Occupancy__c": "occupancy",
    "Appraised_Value__c": "property_value",
    "Base_Loan_Amount__c": "loan_amount",
    "Monthly_Income__c": "monthly_income",
    "Monthly_Debts__c": "monthly_debts",
    "Proposed_Housing_Payment__c": "proposed_housing_payment",
    "Credit_Score__c": "credit_score",
    "Reserves_Liquid__c": "reserves_liquid",
    "Loan_Purpose__c": "loan_purpose",
    "Cash_Out_Amount__c": "cash_out_amount",
    "Property_State__c": "state",
}

_NUMERIC = {"property_value", "loan_amount", "monthly_income", "monthly_debts",
            "proposed_housing_payment", "credit_score", "reserves_liquid", "cash_out_amount"}


def configured() -> bool:
    return bool(os.getenv("SF_USERNAME") and os.getenv("SF_PASSWORD"))


def _client():
    """Import lazily so the package works without simple-salesforce installed."""
    from simple_salesforce import Salesforce
    return Salesforce(
        username=os.environ["SF_USERNAME"],
        password=os.environ["SF_PASSWORD"],
        security_token=os.getenv("SF_SECURITY_TOKEN", ""),
        domain=os.getenv("SF_DOMAIN", "login"),
    )


def _map_record(row: dict) -> Optional[dict]:
    loan: dict = {}
    for sf_field, crux_field in FIELD_MAP.items():
        val = row.get(sf_field)
        if val is None:
            continue
        loan[crux_field] = float(val) if crux_field in _NUMERIC else val
    # required fields present?
    required = ["loan_id", "property_value", "loan_amount", "monthly_income",
                "monthly_debts", "proposed_housing_payment", "credit_score", "reserves_liquid"]
    if not all(k in loan for k in required):
        return None
    loan["credit_score"] = int(loan["credit_score"])
    return {
        "opportunity_id": row.get("Id", loan.get("loan_id")),
        "borrower": row.get("Name", loan.get("loan_id")),
        "initials": "".join(w[0] for w in str(row.get("Name", "L")).split()[:2]).upper() or "L",
        "stage": row.get("StageName", "Underwriting"),
        "story": "Synced from Salesforce",
        "loan": loan,
    }


def list_records(limit: int = 12) -> list[dict]:
    """Records from Salesforce, mapped to LoanFile-shaped dicts. [] if unconfigured."""
    if not configured():
        return []
    try:
        sf = _client()
        fields = ", ".join(["Id", "Name", "StageName", *FIELD_MAP.keys()])
        soql = (f"SELECT {fields} FROM Opportunity "
                f"WHERE StageName = 'Underwriting' ORDER BY LastModifiedDate DESC LIMIT {int(limit)}")
        rows = sf.query(soql).get("records", [])
        out = []
        for r in rows:
            rec = _map_record(r)
            if rec:
                out.append(rec)
        return out
    except Exception:
        # Never take the demo down over a connectivity/field-name issue.
        return []
