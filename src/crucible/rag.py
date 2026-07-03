"""Retrieval over a guideline corpus — real citations, not a hardcoded table.

Pure-Python BM25 (no deps, runs offline and on the MI300X container). The corpus
lives in `corpus/*.md`; each file declares its SOURCE and is split into cited
passages. This is the seam where Astravyx's embedding RAG (or an embedder on the
MI300X) drops in behind the same `retrieve(query) -> [Passage]` interface.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

_CORPUS_DIR = Path(__file__).resolve().parent / "corpus"
_TOKEN = re.compile(r"[a-z0-9]+")


def _tok(s: str) -> list[str]:
    return _TOKEN.findall(s.lower())


@dataclass
class Passage:
    source: str
    heading: str
    text: str
    score: float = 0.0

    @property
    def quote(self) -> str:
        return self.text if len(self.text) <= 240 else self.text[:237] + "…"


def _load_passages() -> list[dict]:
    passages: list[dict] = []
    if not _CORPUS_DIR.exists():
        return passages
    for f in sorted(_CORPUS_DIR.glob("*.md")):
        raw = f.read_text(encoding="utf-8")
        source = f.stem
        lines = raw.splitlines()
        if lines and lines[0].upper().startswith("SOURCE:"):
            source = lines[0].split(":", 1)[1].strip()
            lines = lines[1:]
        heading, buf = "General", []
        def flush():
            if buf:
                text = " ".join(x.strip() for x in buf if x.strip())
                if text:
                    passages.append({"source": source, "heading": heading, "text": text,
                                     "tokens": _tok(heading + " " + text)})
        for ln in lines:
            if ln.startswith("# "):
                flush(); heading = ln[2:].strip(); buf = []
            else:
                buf.append(ln)
        flush()
    return passages


class BM25Index:
    def __init__(self, passages: list[dict], k1: float = 1.5, b: float = 0.75) -> None:
        self.passages = passages
        self.k1, self.b = k1, b
        self.N = len(passages)
        self.avgdl = (sum(len(p["tokens"]) for p in passages) / self.N) if self.N else 0
        df: dict[str, int] = {}
        for p in passages:
            for w in set(p["tokens"]):
                df[w] = df.get(w, 0) + 1
        self.idf = {w: math.log(1 + (self.N - d + 0.5) / (d + 0.5)) for w, d in df.items()}

    def search(self, query: str, k: int = 3) -> list[Passage]:
        q = _tok(query)
        scored: list[tuple[float, dict]] = []
        for p in self.passages:
            tf: dict[str, int] = {}
            for w in p["tokens"]:
                tf[w] = tf.get(w, 0) + 1
            dl = len(p["tokens"]) or 1
            s = 0.0
            for w in q:
                if w in tf:
                    s += self.idf.get(w, 0.0) * (tf[w] * (self.k1 + 1)) / (
                        tf[w] + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1)))
            if s > 0:
                scored.append((s, p))
        scored.sort(key=lambda x: -x[0])
        return [Passage(p["source"], p["heading"], p["text"], round(s, 3)) for s, p in scored[:k]]


_INDEX: BM25Index | None = None


def index() -> BM25Index:
    global _INDEX
    if _INDEX is None:
        _INDEX = BM25Index(_load_passages())
    return _INDEX


def retrieve(query: str, k: int = 3) -> list[Passage]:
    return index().search(query, k)


def top(query: str) -> Passage | None:
    hits = retrieve(query, 1)
    return hits[0] if hits else None


def corpus_size() -> int:
    return index().N
