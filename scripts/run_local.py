"""Run a sample loan through the full Crucible pipeline and print the result.

    python scripts/run_local.py --loan needs_steps
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from crucible.pipeline import run_crucible  # noqa: E402

BADGE = {"fundable_now": "FUNDABLE NOW", "fundable_with_steps": "PATH TO YES", "not_yet": "NOT YET"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--loan", default="needs_steps",
                    help="sample name in data/sample_loans (or a path to a .json)")
    ap.add_argument("--json", action="store_true", help="print raw JSON only")
    args = ap.parse_args()

    p = Path(args.loan)
    if not p.exists():
        p = ROOT / "data" / "sample_loans" / f"{args.loan}.json"
    loan = json.loads(p.read_text())

    result = run_crucible(loan)

    if args.json:
        print(result.model_dump_json(indent=2))
        return

    r = result
    print(f"\n  CRUCIBLE  |  loan {r.loan_id}  |  [{BADGE[r.decision_state]}]")
    m = r.metrics
    print(f"  metrics   DTI {m.dti:.1%}  LTV {m.ltv:.1%}  reserves {m.reserves_months:.1f} mo\n")

    if r.steps:
        print("  Path to Yes:")
        for s in r.steps:
            src = s.citation.source if s.citation else "uncited"
            print(f"    {s.rank}. [{s.effort}] {s.action}")
            print(f"       -> {s.why}  ({src})")
    if r.still_open:
        print("\n  Still blocking:")
        for o in r.still_open:
            src = o.citation.source if o.citation else "uncited"
            print(f"    - {o.adverse_action_reason}  ({src})")

    rr = r.routing_report
    total = rr.local_calls + rr.cloud_calls
    share = (rr.local_calls / total * 100) if total else 0
    print(f"\n  routing   {rr.local_calls} local / {rr.cloud_calls} cloud "
          f"({share:.0f}% on MI300X)  |  {rr.tokens} tok  |  ~${rr.est_cost_usd:.6f}")
    print(f"  audit     every_claim_cited={r.audit.every_claim_has_citation}  "
          f"unverified={r.audit.unverified_flags}\n")


if __name__ == "__main__":
    main()
