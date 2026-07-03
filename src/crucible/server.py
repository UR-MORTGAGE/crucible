"""FastAPI surface. POST a loan, get a PathToYes."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from fastapi import HTTPException

from . import aus, docintel, outreach, rag, salesforce
from .config import load_config
from .learning import STORE as LEARN
from .pipeline import run_crucible, iter_crucible_events
from .scenarios import SCENARIOS
from .schemas import LoanFile, PathToYes

app = FastAPI(title="Crucible", version="0.1.0",
              description="Adversarial, transparent AI underwriting.")

UI_FILE = Path(__file__).resolve().parents[2] / "ui" / "index.html"

# The active case files: loan_id -> {"loan": LoanFile, "result": PathToYes,
# "documents": [...], "outreach": [...], "aus": {...}}. In-memory for the demo;
# production swaps in a store without changing the endpoints.
WORKFILES: dict[str, dict] = {}


def _store_workfile(loan_dict: dict, result: PathToYes) -> None:
    WORKFILES[result.loan_id] = {
        "loan": LoanFile(**loan_dict),
        "result": result,
        "documents": [],
        "outreach": [],
        "aus": None,
    }


def _workfile(loan_id: str) -> dict:
    wf = WORKFILES.get(loan_id)
    if not wf:
        raise HTTPException(404, f"No workfile for {loan_id}; underwrite it first.")
    return wf


class UnderwriteRequest(BaseModel):
    loan: dict


class DocumentUpload(BaseModel):
    filename: str = "document"
    text: str = ""
    fields: dict | None = None
    doc_type: str | None = None


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    """The demo UI — the loan on trial."""
    if UI_FILE.exists():
        return UI_FILE.read_text(encoding="utf-8")
    return "<h1>Crucible</h1><p>UI not found; POST /underwrite.</p>"


@app.get("/health")
def health() -> dict:
    cfg = load_config()
    return {"status": "ok", "mode": cfg.mode}


@app.get("/scenarios")
def scenarios() -> list[dict]:
    """The borrower persona library shown in the demo docket."""
    return SCENARIOS


# Salesforce-shaped Opportunity ids for the ingest demo. In production this
# endpoint queries the underwrite LWC's Opportunity/loan records via Apex/SOQL
# and maps them to LoanFile; here it returns the personas in that shape.
_SF_OPP_IDS = ["0065f00000AqR1xAAG", "0065f00000BvT4mAAG", "0065f00000CwU7nAAG",
               "0065f00000DxV9pAAG", "0065f00000EyW2qAAG"]


@app.get("/ingest/salesforce")
def ingest_salesforce() -> dict:
    """Loan records from Salesforce (the underwrite LWC).

    Live when SF creds are configured; otherwise the demo personas, in the same
    shape, so the UI always works.
    """
    live = salesforce.list_records()
    if live:
        return {"source": "salesforce", "records": live}

    out = []
    for i, p in enumerate(SCENARIOS):
        out.append({
            "opportunity_id": _SF_OPP_IDS[i % len(_SF_OPP_IDS)],
            "borrower": p["name"],
            "initials": p["initials"],
            "stage": "Underwriting",
            "story": p["story"],
            "expected": p["expected"],
            "loan": p["loan"],
        })
    return {"source": "mock" if not salesforce.configured() else "salesforce_empty", "records": out}


@app.post("/underwrite", response_model=PathToYes)
def underwrite(req: UnderwriteRequest) -> PathToYes:
    result = run_crucible(req.loan)
    _store_workfile(req.loan, result)
    return result


@app.get("/workfile/{loan_id}")
def get_workfile(loan_id: str) -> dict:
    wf = _workfile(loan_id)
    return {
        "loan_id": loan_id,
        "result": wf["result"].model_dump(),
        "documents": wf["documents"],
        "outreach": wf["outreach"],
        "aus": wf["aus"],
    }


@app.post("/workfile/{loan_id}/documents")
def upload_document(loan_id: str, doc: DocumentUpload) -> dict:
    """The agent analyzes an incoming document and auto-clears what it satisfies."""
    wf = _workfile(loan_id)
    report = docintel.apply_document(doc.model_dump(), wf["result"].conditions, wf["loan"])
    for c in report["cleared"]:
        LEARN.record_clearance(c["code"], report["doc_type"])
    wf["documents"].append(report)
    return report


@app.post("/workfile/{loan_id}/outreach")
def run_outreach(loan_id: str) -> dict:
    """The agent plans + dispatches contact for every open condition."""
    wf = _workfile(loan_id)
    plan = outreach.build_plan(wf["result"].conditions, wf["loan"])
    plan = outreach.dispatch(plan)
    wf["outreach"] = plan
    return {"loan_id": loan_id, "items": plan,
            "live": outreach._twilio_configured()}


@app.post("/workfile/{loan_id}/aus")
def submit_aus(loan_id: str) -> dict:
    """Submit the (possibly restructured) file to the AUS seam (DU/LPA or simulated)."""
    wf = _workfile(loan_id)
    result = aus.submit(wf["loan"])
    wf["aus"] = result
    return result


@app.get("/learning")
def learning_summary() -> dict:
    """What the agent has learned across every file it has underwritten."""
    return LEARN.summary()


@app.get("/guidelines/search")
def guidelines_search(q: str, k: int = 3) -> dict:
    """Ask the guideline corpus directly (the RAG surface)."""
    hits = rag.retrieve(q, k=k)
    return {"query": q, "corpus_passages": rag.corpus_size(),
            "hits": [{"source": h.source, "heading": h.heading,
                      "score": h.score, "quote": h.quote} for h in hits]}


@app.post("/underwrite/stream")
async def underwrite_stream(req: UnderwriteRequest) -> StreamingResponse:
    """Server-sent events: the proceeding streams in, event by event."""
    async def gen():
        for event, payload in iter_crucible_events(req.loan):
            if event == "done":  # capture the workfile so the agentic endpoints can act on it
                try:
                    _store_workfile(req.loan, PathToYes(**payload))
                except Exception:
                    pass
            yield f"event: {event}\ndata: {json.dumps(payload)}\n\n"
            await asyncio.sleep(0.28)  # pacing so the debate reads live
        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
