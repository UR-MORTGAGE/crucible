"""Adaptive learning loop.

Every file Crucible underwrites is recorded; the model nudges its weights toward
what actually approves. It exposes an approval-likelihood score and learns which
restructure moves work, so the solver's ordering improves over time.

This is an honest, online, explainable scorer — and the seam where a model
fine-tuned on your book (on the MI300X) drops in later behind the same interface.
"""
from __future__ import annotations

import json
import math
import threading
from pathlib import Path

from .schemas import LoanFile, Projected

_STATE_FILE = Path(__file__).resolve().parents[2] / "data" / "learning_state.json"

# Feature scaling anchors (conventional). Signals are relative, so this is fine
# even for FHA files — it's a monotonic approvability signal, not a rule check.
_ANCHORS = {"dti": 0.50, "ltv": 0.97, "fico": 620, "res": 2.0}


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(min(x, 30), -30)))


def _features(loan: LoanFile, m: Projected) -> dict[str, float]:
    return {
        "dti": (_ANCHORS["dti"] - (m.dti or 0)) * 4,          # margin under the DTI cap
        "ltv": (_ANCHORS["ltv"] - (m.ltv or 0)) * 4,
        "fico": (loan.credit_score - _ANCHORS["fico"]) / 60,
        "res": ((m.reserves_months or 0) - _ANCHORS["res"]) / 4,
    }


class LearningStore:
    def __init__(self) -> None:
        self.weights = {"dti": 1.4, "ltv": 1.0, "fico": 1.1, "res": 0.6}
        self.bias = 0.2
        self.n = 0
        self.move_stats: dict[str, list[int]] = {}       # action -> [successes, total]
        self.clearance_stats: dict[str, dict] = {}       # cond code -> {count, by_doc: {doc_type: n}}
        self._lock = threading.Lock()                    # streams run on worker threads
        self._load()

    # ---- persistence (best-effort; never crash the request) ----
    def _load(self) -> None:
        try:
            d = json.loads(_STATE_FILE.read_text())
            self.weights.update(d.get("weights", {}))
            self.bias = d.get("bias", self.bias)
            self.n = d.get("n", 0)
            self.move_stats = d.get("move_stats", {})
            self.clearance_stats = d.get("clearance_stats", {})
        except Exception:
            pass

    def _save(self) -> None:
        try:
            _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            _STATE_FILE.write_text(json.dumps({
                "weights": self.weights, "bias": self.bias, "n": self.n,
                "move_stats": self.move_stats, "clearance_stats": self.clearance_stats,
            }, indent=2))
        except Exception:
            pass

    # ---- scoring ----
    def score(self, loan: LoanFile, m: Projected) -> float:
        f = _features(loan, m)
        z = self.bias + sum(self.weights[k] * f[k] for k in f)
        return round(_sigmoid(z), 4)

    # ---- learning ----
    def record(self, loan: LoanFile, m: Projected, approved: bool, lr: float = 0.05) -> None:
        with self._lock:
            f = _features(loan, m)
            pred = self.score(loan, m)
            err = (1.0 if approved else 0.0) - pred      # perceptron/logistic delta
            for k in self.weights:
                self.weights[k] += lr * err * f[k]
            self.bias += lr * err
            self.n += 1
            self._save()

    def record_moves(self, actions: list[str], success: bool) -> None:
        with self._lock:
            for a in actions:
                s = self.move_stats.setdefault(a, [0, 0])
                s[1] += 1
                if success:
                    s[0] += 1
            self._save()

    def move_success_rate(self, action: str) -> float:
        s = self.move_stats.get(action)
        if not s or s[1] == 0:
            return 0.5                                   # neutral prior
        return s[0] / s[1]

    def record_clearance(self, code: str, doc_type: str) -> None:
        """A condition cleared by a document — the agent learns which docs
        clear which conditions, sharpening future outreach + doc requests."""
        with self._lock:
            s = self.clearance_stats.setdefault(code, {"count": 0, "by_doc": {}})
            s["count"] += 1
            s["by_doc"][doc_type] = s["by_doc"].get(doc_type, 0) + 1
            self._save()

    def summary(self) -> dict:
        return {
            "files_underwritten": self.n,
            "weights": {k: round(v, 4) for k, v in self.weights.items()},
            "bias": round(self.bias, 4),
            "restructure_moves": {
                a: {"successes": s[0], "attempts": s[1],
                    "success_rate": round(s[0] / s[1], 3) if s[1] else None}
                for a, s in self.move_stats.items()
            },
            "condition_clearances": self.clearance_stats,
        }


# Process-wide singleton — the loop that learns across every underwrite.
STORE = LearningStore()
