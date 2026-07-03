"""Start the Crucible API + demo UI. PATH-proof: run it with the venv's python
and you never need `uvicorn` on PATH or an activated shell.

    python scripts/serve.py
    # or, without activating the venv:
    .\.venv\Scripts\python.exe scripts\serve.py

Then open http://127.0.0.1:8000
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import uvicorn  # noqa: E402

if __name__ == "__main__":
    print("Crucible -> http://127.0.0.1:8000  (Ctrl+C to stop)")
    uvicorn.run("crucible.server:app", host="127.0.0.1", port=8000, reload=False)
