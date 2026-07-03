# CRUCIBLE

**Adversarial, transparent AI underwriting for the AMD Developer Hackathon — Act II (Unicorn Track).**

> Every lender's AI tells a borrower *no*. Crucible puts the loan in the crucible —
> an Adversary tries to kill it, an Advocate fights to save it, an Adjudicator rules
> on the cited record — and the borrower walks away with a ranked **Path to Yes**.

Team: **Milad + Joseph** · Build window: **Jul 6 → 11, 2026** · Deadline: **Jul 11, 15:00 UTC**

**→ Full capability outline: [CAPABILITIES.md](CAPABILITIES.md)** · integration plan: [INTEGRATION.md](INTEGRATION.md) · roadmap: [ROADMAP.md](ROADMAP.md)

---

## ⚠️ Isolation guarantee

This is a **standalone repository**. It has:

- its **own folder** (`C:\Users\Ur Mortgage\crucible`) — nothing outside it is touched;
- its **own virtual environment** (`.venv`) — created below, not shared;
- **zero imports from Astravyx, AOPE, or any existing project.**

Running or installing Crucible cannot affect the Astravyx AI system or any other repo.
Nothing here reads or writes Astravyx paths, its Chroma DB, or its `.env`.

---

## Quick start (mock mode — no GPU, no API keys)

Crucible runs end-to-end in **mock mode** out of the box so you can see the whole
Adversary → Advocate → Adjudicator flow before any AMD hardware is provisioned.
The mock path computes **real** DTI / LTV / reserves math locally; only the LLM
reasoning is stubbed.

```powershell
# from C:\Users\Ur Mortgage\crucible
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# run a sample loan through the full pipeline (CLI)
python scripts\run_local.py --loan needs_steps

# start the app + demo UI (PATH-proof launcher — no activation needed)
.\.venv\Scripts\python.exe scripts\serve.py
#   -> open http://127.0.0.1:8000   (the Tribunal demo UI)
```

## The demo UI — "the loan on trial"

`http://127.0.0.1:8000` serves a full product surface (a judicial-dossier /
trading-terminal aesthetic):

- **Live streaming proceeding** (real SSE): Prosecution (Adversary) files cited
  charges, Defense (Advocate) answers each, the bench (Adjudicator) stamps a verdict.
- **Editable loan file + live what-if** — drag any input, watch the metrics and the
  predicted verdict update; re-run to see the decision change.
- **Router control room** — hybrid-vs-all-frontier cost, % handled on MI300X,
  per-step routing trace, projected savings at scale.
- **Compliance export** — download a Path-to-Yes borrower letter, a Reg-B
  adverse-action notice, and the raw `PathToYes` JSON.
- **Persona library**, **Demo mode** (auto-plays all four borrowers), keyboard
  shortcuts (`1-4`, `R`, `D`, `E`, `S`, `?`), and an offline engine fallback so it
  renders even with no backend.

Endpoints: `GET /` (UI) · `POST /underwrite` · `POST /underwrite/stream` (SSE) ·
`GET /scenarios` · `GET /health`.

## Going live on AMD (Day 1+)

1. Copy `.env.example` → `.env`, set `CRUCIBLE_MODE=live`.
2. Serve an open model on the **MI300X** via vLLM/ROCm (see `docker-compose.yml`),
   point `LOCAL_LLM_BASE_URL` at it.
3. Add your `FIREWORKS_API_KEY` for the cloud reasoning lane.
4. `docker compose up` brings up vLLM + the Crucible API together on ROCm.

## Layout

```
src/crucible/
  config.py            env + thresholds
  schemas.py           PathToYes and friends (pydantic)
  router.py            hybrid router: local (MI300X) vs cloud (Fireworks)
  telemetry.py         routing cost/token ledger
  retrieval/           guideline retrieval + metric math (the local lane)
  clients/             local vLLM client, Fireworks client, mock client
  agents/              Adversary / Advocate / Adjudicator + orchestrator
  pipeline.py          run_crucible(loan) -> PathToYes
  server.py            FastAPI surface
data/sample_loans/     easy_yes / needs_steps / not_yet
scripts/run_local.py   CLI runner
tests/test_smoke.py    offline import + schema checks
```

## Who owns what (per the build spec)

- **Joseph** — router, agents, AMD/ROCm infra, demo UI.
- **Milad** — the 3 real loan files, validating every guideline citation, the
  business-value + on-camera pitch.
