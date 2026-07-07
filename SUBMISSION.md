# lablab Submission Package — copy-paste ready

Every field below maps to the lablab submission form. Fill assets marked ⏳,
then submitting is a 5-minute paste job. **Deadline: Sat Jul 11, 15:00 UTC
(11:00 AM ET). We submit by 10:00 AM ET.**

---

## Title
**Crucible — the autonomous AI underwriter**

## Short description / tagline (≤ ~140 chars)
> The autonomous underwriter that puts loans on trial, works the conditions,
> and rebuilds denials — every claim cited, on AMD MI300X.

## Long description
> Every lender's AI ends a hard loan with one word: no. Crucible is an
> autonomous AI underwriter that works the file until it's a yes.
>
> A loan is pulled straight from the system of record (Salesforce) and put on
> trial before three adversarial agents: a Prosecutor that files every reason
> to deny — each cited to retrieved guideline text (Fannie Mae, HUD 4000.1) —
> a Defender that answers every charge with a guideline-valid path, and an
> Adjudicator that rules on the cited record and issues a ranked "Path to Yes"
> with Reg-B adverse-action reasons for anything still blocking.
>
> The verdict is where Crucible starts, not stops. It writes the underwriter's
> real conditions report (Master / TRAC / PTD sections with industry codes),
> reads incoming documents and auto-clears the conditions they satisfy — with
> sufficiency math, so a $900 bank statement does not clear a $31,400 funds
> condition — plans outreach to the humans who owe the rest (title company,
> insurance agent, borrower — Twilio rails), and submits down the Fannie/
> Freddie AUS seam. When a file is denied, its restructure solver searches
> buydowns, product switches, and down-payment moves to rebuild the deal —
> and writes the change-of-circumstance conditions automatically. It learns
> from every file: approval scoring, restructure success rates, and which
> documents clear which conditions.
>
> AMD is load-bearing, not decorative: guideline RAG, deterministic
> underwriting math, adversary scans, and document parsing run locally on an
> AMD Instinct MI300X (vLLM on ROCm) — borrower PII never leaves the box —
> while only the hardest reasoning escalates to Fireworks. A live router
> ledger shows ~60% of calls handled on-device and the cost vs. an
> all-frontier pipeline.
>
> The console ships with a voiced guided tour: Crucible himself walks the
> platform, pulls a live file, and underwrites it in front of you — in
> seconds, not days.

## Technology tags
AMD Developer Cloud · AMD Instinct MI300X · ROCm · vLLM · Fireworks AI ·
FastAPI · Python · Salesforce · Twilio · Docker

## Category / track
**Unicorn Track**

## Links
| Field | Value | Status |
|---|---|---|
| Public GitHub repo | https://github.com/UR-MORTGAGE/crucible *(flip to **public** before submitting: `gh repo edit UR-MORTGAGE/crucible --visibility public`)* | ✅ pushed (private until submit day) |
| Demo URL (interim, live NOW) | https://steal-requesting-scanner-related.trycloudflare.com *(tunnel → local box; only up while serve.py + cloudflared run)* | ✅ live |
| Demo URL (final) | `http://<AMD-instance-ip>:8080` from `deploy/amd_deploy.sh` — swap in after MI300X deploy | ⏳ |
| Video | YouTube (unlisted) — record the console tour (press **T**), ~2.5 min | ⏳ record after live deploy |
| Slide deck | Export/print the deck artifact to PDF + attach; live link optional | ⏳ export |

## Cover image
Screenshot the dedicated cover stage (1920×1080, 3D tribunal cards + crucible +
ember field): https://claude.ai/code/artifact/4b813cdf-ac48-4771-b029-0a77c4b329f8
— press ⛶ Fullscreen, then PrtScn (or Win+Shift+S the frame).

## Video script
Press **T** in the console with the backend live — Crucible narrates and
drives the whole demo himself (tour ≈ 2.5 min, includes the
"seconds-not-days" business beat). Record 1080p with OBS/Game Bar; add the
15-second title card from the teleprompter plan.

## Containerization statement (form question)
> Fully containerized: `docker compose up` brings up vLLM-on-ROCm (MI300X)
> plus the Crucible service (Dockerfile included). One-command deploy script
> at `deploy/amd_deploy.sh`.

## Pre-submit checklist (Friday)
- [ ] MI300X deploy done; routing trace screenshot saved (local + Fireworks lanes live)
- [ ] Video recorded against LIVE backend, uploaded, link works logged-out
- [ ] Repo flipped **public**; clean-clone `docker build` passes
- [ ] Demo URL reachable from a phone
- [ ] Cover image uploaded
- [ ] Every form field pasted from this file
- [ ] Screenshot the completed form + the submission receipt
