# Integrating Crucible into Astravyx (post-hackathon)

**Do this AFTER July 11.** During the hackathon Crucible stays standalone — that
protects the clean container, the AMD showcase, and Astravyx itself. This doc
captures the plan (and the landmines) so future-you doesn't rediscover them.

## The relationship

- **Astravyx = the brain / knowledge source.** Guideline corpus, compliance
  firewall, the 7 lobes, the vector DB.
- **Crucible = the underwriting engine that graduates *into* Astravyx.** The
  adversarial "path to yes" is a better version of what `src/uwm/` already does.
- **Astravyx's underwriting section = the interactive audit log** — the surface
  that renders Crucible's `PathToYes` (debate + steps + routing + audit trail).

So: Crucible is the backend, Astravyx's underwriting UI is the front-end/log.
Not either/or — both, in that order.

## The seams (already built for this)

1. **Import, don't fork.** Astravyx depends on the Crucible package and calls
   `run_crucible(loan) -> PathToYes`. Crucible's repo stays the source of truth.
2. **Swap the guideline layer, not the interface.** `GuidelineRetriever.retrieve(loan)
   -> list[Citation]` is a deliberate seam. Point it at Astravyx's real corpus;
   nothing downstream changes.
3. **Map the loan.** Reuse Astravyx `src/uwm/` FIELD_MAP to build Crucible's
   `LoanFile` from a UWM export.

## Landmines (hard-won — do not trip these)

- ⚠️ **ChromaDB is single-process.** Crucible-in-Astravyx must query the vector DB
  through Astravyx's *existing* owner process. Never open a second client against a
  live index or the HNSW file corrupts (`Error loading hnsw index`). Retrieval goes
  through Astravyx's retriever, not a fresh Chroma connection.
- ⚠️ **One compliance firewall, not two.** Crucible's cited-or-silent +
  Reg-B adverse-action mirrors Astravyx's ECOA/Reg-B firewall. Unify them into a
  single authority; don't run two that can disagree.
- ⚠️ **Router is optional inside Astravyx.** Astravyx runs its own models; the
  local/cloud split is a hackathon concern. Keep the router interface but let
  Astravyx inject its own client map.

## Phasing

- **Phase 1** — import Crucible as the underwriting engine; repoint
  `GuidelineRetriever`; unify the firewall.
- **Phase 2** — Astravyx underwriting section becomes the Crucible log/surface
  (render the debate + `PathToYes` + routing report as a per-loan audit trail).

See also [ROADMAP.md](ROADMAP.md) for the product features that ride the same engine.
