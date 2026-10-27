"""Ricerca fuzzy dei parametri device per nome (VST inclusi). Logica pura."""
from __future__ import annotations
import re
from difflib import SequenceMatcher


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def find_param(names: list[str], query: str, min_score: float = 0.55) -> int | None:
    """Indice del parametro che meglio matcha `query` (substring > fuzzy)."""
    q = _norm(query)
    if not q:
        return None
    best_i, best_score = None, 0.0
    for i, name in enumerate(names):
        n = _norm(str(name))
        if not n:
            continue
        if q == n:
            return i
        score = 0.9 if (q in n or n in q) else SequenceMatcher(None, q, n).ratio()
        if score > best_score:
            best_i, best_score = i, score
    return best_i if best_score >= min_score else None
