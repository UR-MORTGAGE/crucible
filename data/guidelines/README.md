# Guideline corpus

Drop the real guideline documents here (Fannie/Freddie Selling Guides, HUD 4000.1,
investor/UWM overlays) for the live RAG retriever. Bulk files are gitignored — only
this README is tracked.

In mock mode nothing here is required: the thresholds and citations live in
`src/crucible/retrieval/guidelines.py`. Going live, point a real retriever at this
folder and keep the same `retrieve(loan) -> list[Citation]` interface.
