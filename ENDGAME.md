# ENDGAME — July 6–11 runbook

Mission: kill every item on the losing list. Deadline: **Sat Jul 11, 15:00 UTC = 11:00 AM ET.**
We submit by **10:00 AM ET** — one hour of buffer, no exceptions.

Roles: **Joseph** = deploy/infra/record · **Milad** = domain validation/pitch/on-camera.
Rule of the week: **the live MI300X run outranks every other task.**

---

## Before July 6 (prep — do now)

- [ ] **AMD AI Developer Program** — BOTH of you signed up (credits gate; late signup burns Day 1)
- [ ] **lablab team** created (Discord server joined — membership, not just account link), both members on it
- [ ] **Git**: `git init` this repo (it is NOT under git yet) → set local user (UR-MORTGAGE / miladr15@gmail.com) → create **private** GitHub repo `UR-MORTGAGE/crucible` → push. Flip public on submission day, not before.
- [ ] **Fireworks account** created; know where the hackathon credits land
- [ ] **Backup video**: record one full teleprompter take in mock mode now. If everything goes wrong later, we still have a submission video.
- [ ] Dry-run: `scripts\serve.py` → run all 5 personas → docs → O → A. Note any visual nits.

---

## Mon Jul 6 — DEPLOY DAY (nothing else matters)

**Gate to pass today: the routing trace shows real inference — local lane on MI300X, escalation lane on Fireworks.**

1. Track specs drop → Joseph skims Track 1 (10 min, decide later; Unicorn is primary).
2. Provision AMD Developer Cloud MI300X instance.
3. `docker pull rocm/vllm` → **pin the exact tag that works**, serve an open model
   (Llama-3.1-8B-Instruct first; drop to a smaller model if VRAM/download drags).
4. Smoke: `curl :8000/v1/chat/completions` returns tokens.
5. Clone repo on the box → `.env`: `CRUCIBLE_MODE=live`, `LOCAL_LLM_BASE_URL`,
   `FIREWORKS_API_KEY`, `CRUCIBLE_LLM_PROVIDER=fireworks`.
6. `docker compose up` → hit `/health` (mode=live) → run James end-to-end.
7. **Capture proof**: screenshot + screen recording of the router control room
   showing MI300X + Fireworks lanes live. Post in team chat. This is the artifact
   that saves us if anything regresses later.

**Contingencies:** instance unavailable → open a support ticket in the hackathon
Discord *immediately*, keep building in mock. vLLM image broken → try
`rocm/vllm-dev` tags or a smaller model. Fireworks credits missing → personal key.

## Tue Jul 7 — LIVE HARDENING + PUBLIC URL

- Run all 5 personas + full workfile loop (docs/O/A) against live inference; fix anything that only breaks live (timeouts, token limits, SSE pacing).
- Stand up the **public demo URL** (lablab requires it): open port on the AMD box or a cloudflared/ngrok tunnel to the container. Confirm it loads from a phone.
- Decide Track 1: if the routing-agent spec is close to our router, carve out the submission (≤ half a day, else skip — Unicorn is the prize).
- Evening: Milad walks the live app as a skeptical underwriter; log every wrong-feeling wording.

## Wed Jul 8 — MILAD DAY (domain truth) + polish

- Milad: replace placeholder guideline quotes in `src/crucible/corpus/*.md` with exact current text; validate every condition's wording; supply 3 real-shaped sanitized loan files for the personas.
- Joseph: apply Tuesday's nit list; optional stretch **only if green**: Fireworks fine-tune of a small guideline-QA model (allowed by rules — one more "meaningful tech" line for the pitch).
- Freeze the product at end of day. **No new features after Wednesday.**

## Thu Jul 9 — RECORD DAY

- Record against the **live** backend (status dot must say live).
- Teleprompter (1:48) on second screen; 2–3 full takes; OBS/Game Bar 1080p; quiet room, close mic, 2s room tone.
- Add 15s title card → ~2:05 final cut (Clipchamp). Milad voices business-value beats if splitting narration.
- Capture stills during takes → cover image (Tribunal masthead mid-verdict) + deck screenshots.
- Upload video (YouTube unlisted) same day — never leave upload for Saturday.

## Fri Jul 10 — SUBMISSION DRY-RUN (treat as the real deadline)

- Repo: flip **public**; README top = one-paragraph pitch + video link + demo URL; CAPABILITIES/ENDGAME clean.
- **Clean-clone test**: fresh `git clone` → `docker build` → container runs. (Judges' reproducibility check.)
- Fill EVERY lablab field: title · description · **cover image** · **video** · **slide deck** (export PDF too) · **public repo link** · **demo URL** · containerization noted.
- Save/submit draft if the platform allows. Screenshot the completed form.
- Buffer day for whatever broke.

## Sat Jul 11 — SUBMIT

- 09:00 ET: final pass — demo URL up? video plays? repo public? every field filled?
- **10:00 ET: SUBMIT.** Confirm on-screen receipt; screenshot it.
- Touch nothing afterward. 11:00 ET deadline passes with us already in.

---

## The losing list → where it dies

| Risk | Killed on |
|---|---|
| Never ran on MI300X | Mon (gate + proof capture) |
| Credits gate | Prep week (Program signup) |
| Video is the judging surface | Thu (live recording, backup from prep week) |
| Fireworks not visible | Mon step 7 (trace proof) |
| "Too niche" | Deck roadmap slide (already in) |
| Checklist/deadline miss | Fri dry-run + Sat 10:00 ET submit |
