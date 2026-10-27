"""Wake word: logica pura e testabile. Whisper può scrivere 'livemind',
'live mind', 'live-mind', 'laiv maind'... → matching fuzzy sulle prime parole."""
from __future__ import annotations
import re
from difflib import SequenceMatcher

WAKE_WORD = "livemind"
FUZZY_THRESHOLD = 0.72


def _normalize(text: str) -> str:
    t = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(t.split())


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def extract_command(text: str, wake: str = WAKE_WORD) -> str | None:
    """Se il testo inizia con la wake word (anche storpiata), ritorna il comando
    dopo di essa. Altrimenti None (frase ignorata)."""
    t = _normalize(text)
    if not t:
        return None
    words = t.split()
    # prova 1 parola ("livemind") e 2 parole ("live mind", "laiv maind")
    for n in (1, 2):
        head = "".join(words[:n])
        if _similar(head, wake) >= FUZZY_THRESHOLD:
            return " ".join(words[n:]).strip()
    return None
