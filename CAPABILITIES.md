# Crucible — Full Capabilities

**Crucible is an autonomous AI underwriter.** It ingests a loan file from the
system of record, puts it on trial before three adversarial agents, writes the
underwriter's real conditions report, reads incoming documents and clears
conditions itself, contacts the humans who owe the rest, submits down the AUS
rails, rebuilds denied deals, and learns from every file it touches — with
every claim cited to guideline text or not made at all.

Runs on **AMD Instinct MI300X (ROCm/vLLM) + Fireworks AI**, fully containerized.

---

## 1 · Intake — the file comes to the agent

| Source | How |
|---|---|
| **Salesforce** | `GET /ingest/salesforce` — SOQL against the underwrite LWC's Opportunity via `FIELD_MAP` (`salesforce.py`); live with `SF_*` creds, demo personas otherwise. Click a record → pulled + underwritten. |
| **Upload** | Drag a 1003-style JSON loan file into the console. |
| **Manual** | Hand-key a file; sliders double as the underwriter's **what-if override** on any pulled file. |

Five demo personas cover the outcome space: clean approval, DTI-over,
thin-reserves, buydown-rescuable denial, hard denial.

## 2 · The Tribunal — adversarial, cited decisioning

- **Adversary** prosecutes: every reason to deny, each grounded in real math
  and cited to retrieved guideline text.
- **Advocate** defends: the strongest guideline-valid path around each charge
  (product switch, investor, borrower action).
- **Adjudicator** rules on the cited record only — abstains when uncited,
  ranks a **Path to Yes**, and writes Reg-B adverse-action reasons for
  anything still blocking.
- The proceeding **streams live** over SSE (`POST /underwrite/stream`):
  opening → charges → defenses → verdict → restructure → conditions → routing.

**Dimensions underwritten** (deterministic core engine, `core.py`):
DTI / LTV / credit score / reserves against program ceilings (conventional +
FHA), **Chapter 7 seasoning** (48 mo), **foreclosure seasoning** (84 mo),
**open judgments & liens** (pay/subordinate), credit inquiries, undisclosed
liabilities.

**Retrieval-grounded citations (RAG):** BM25 index over a guideline corpus
(Fannie Mae Selling Guide, Eligibility Matrix, HUD 4000.1). Citation quotes
come from retrieved passages — swapped only when the passage's source matches
the rule. Ask the corpus anything: `GET /guidelines/search?q=...`. The
retriever interface is drop-in compatible with a full corpus (Astravyx) or an
embedding model on the MI300X.

## 3 · Conditions — the real underwriter's output

Generates a sectioned, coded conditions report in industry shape
(Master / TRAC / Underwriter II (PTD) / Disclosures-Compliance (PTD) /
Underwriter To Obtain And Clear) with real trigger logic: appraisal waiver,
temporary-buydown agreement, excess cash-back restructure, clear-title +
judgment payoff/subordination (dual 0064), short-funds-to-close with computed
dollar amounts, HOI (purchase vs. refi renewal), tangible-benefit LOX,
inquiry LOX, missing liabilities, the 1003/counseling/H-3/SSP/state
disclosure set, and **0571 change-of-circumstance conditions emitted by the
restructure solver**.

## 4 · Document intelligence — reads and clears, with judgment

`POST /workfile/{id}/documents` — the agent classifies incoming docs
(bank statement, HOI declarations, LOX, title report, buydown agreement,
1003, credit supplement, disclosures…), extracts the numbers, and
**auto-clears the conditions each doc satisfies** — with sufficiency checks:

- a bank statement clears short-funds **only if** the verified balance covers
  the computed requirement (`verified $41,250 against $31,400 required`);
- an HOI dec page clears **only if** dwelling coverage covers the loan;
- insufficient docs are reported honestly, never cleared.

Parsing runs **locally on the MI300X — borrower PII never leaves the box**.
The parser seam (`DOC_PARSER_URL`) accepts any external document model
(e.g. Nemotron Parse) without downstream changes.

## 5 · Autonomous outreach — works the phones

`POST /workfile/{id}/outreach` — for every open condition the agent decides
**who owes it** (title company, insurance agent, broker, borrower, closing,
TRAC), picks the channel (call / SMS / email), drafts the message referencing
the exact condition, and dispatches: **real Twilio SMS** when creds are set,
honest `queued (demo)` otherwise. Voice rides the same seam (existing dialer
infrastructure plugs in).

## 6 · Restructure solver — denied files get rebuilt

When a file can't fund as submitted, the solver searches allowable moves —
FHA product switch, larger down payment (COC), cash-in reduction (capped at
realistic ≤20%), debt paydown (≤50%), reserve seasoning, 2-1 temporary
buydown — in 1–2-move combinations, and returns the **minimal-borrower-effort
restructure that flips the decision**, with the projected metrics and the
0571 COC conditions written automatically. When nothing realistic clears it,
it says so and refers to manual structuring.

## 7 · AUS rails — Fannie/Freddie seam

`POST /workfile/{id}/aus` builds a DU-style casefile and submits to the
configured endpoint (`DU_API_URL`/`LPA_API_URL` — real access requires
approved-vendor onboarding). Until then it returns DU-shaped findings from
its own engine, **clearly labeled `crucible_simulated`** — Approve/Eligible,
Approve/Eligible (with conditions), or Refer/Caution.

## 8 · Learning — every file makes it smarter

Persistent, explainable online learning (`GET /learning`):

- **Approval scorer** — logistic weights over DTI/LTV/FICO/reserve margins,
  updated on every underwrite; surfaces as the verdict's approval-score chip.
- **Restructure memory** — success rate of every move the solver has tried.
- **Clearance map** — which document types clear which condition codes.

This is the seam where a model fine-tuned on the lender's book (trained on
the MI300X) drops in behind the same interface.

## 9 · Compliance — the moat

- **Cited-or-silent** firewall: no claim without a retrieved citation;
  unverified items are flagged in the audit block, never asserted.
- One-click export: **Path-to-Yes borrower letter**, **Reg-B/ECOA
  adverse-action notice**, and the full machine-readable `PathToYes` JSON.
- Every run carries a routing + audit trail suitable for regulator replay.

## 10 · AMD-native hybrid architecture

- **Router** (`router.py`): per-step policy — retrieval, metric math,
  adversary scan, and document parsing stay **local on the MI300X**
  (vLLM + ROCm); advocate synthesis and adjudication escalate to
  **Fireworks** only on the hard-reasoning steps, with a confidence
  threshold for escalation. Sensitive steps are pinned local.
- Live **token/cost ledger**: ~60% of calls on-device, hybrid-vs-all-frontier
  cost comparison, per-step routing trace, escalation count.
- Cloud-lane provider is pluggable (`CRUCIBLE_LLM_PROVIDER`):
  `fireworks` (default) · `anthropic` (Claude Fable 5 w/ Opus fallback) · `local`.
- **Mock mode** runs the entire pipeline with no GPU and no keys (real math,
  stubbed LLMs) — `docker compose up` brings up vLLM-on-ROCm + the app.

## 11 · The console (single-page UI)

Live-streaming tribunal (prosecution/defense columns with charge↔defense
tendrils, verdict stamp, learned-score chip) · editable file with predicted
verdict · conditions board with per-section counts and **flash-on-clear** ·
document drop zone + one-click sample docs + clearance log · outreach queue ·
AUS badge · autonomous-restructure panel · router control room · audit
ledger · learning card · compliance export · guided demo autoplay · keyboard
shortcuts (1-5, R, O, A, E, D, S) · offline fallback so the demo never dies.

## 12 · API surface

```
GET  /                              console UI
GET  /health · /scenarios · /learning
GET  /ingest/salesforce             pull loans from the system of record
GET  /guidelines/search?q=          ask the guideline corpus (RAG)
POST /underwrite                    loan in → PathToYes out
POST /underwrite/stream             the proceeding, streamed (SSE)
GET  /workfile/{loan_id}            the live case file
POST /workfile/{loan_id}/documents  doc in → conditions auto-cleared
POST /workfile/{loan_id}/outreach   plan + dispatch contact per condition
POST /workfile/{loan_id}/aus        submit down the AUS rails
```

## Honesty table — live vs. seamed

| Capability | Status |
|---|---|
| Tribunal, conditions, doc intelligence, restructure, learning, RAG, router, exports, UI | **Fully working now** (mock LLM lane; real math + retrieval) |
| MI300X/vLLM + Fireworks inference | **Wired** — activates with AMD Dev Cloud + `FIREWORKS_API_KEY` (`CRUCIBLE_MODE=live`) |
| Salesforce pull | **Wired** — activates with `SF_*` creds + org field names in `FIELD_MAP` |
| Twilio SMS outreach | **Wired** — activates with `TWILIO_*` creds; voice = seam |
| Fannie DU / Freddie LPA | **Seam** — requires vendor onboarding; simulated findings clearly labeled until then |
| External doc parser (e.g. Nemotron Parse) | **Seam** (`DOC_PARSER_URL`); local parsing works today |

**Tests:** 21/21 passing (`pytest`) — engine, conditions, restructure,
docintel, outreach, AUS, learning, RAG grounding, endpoints.
