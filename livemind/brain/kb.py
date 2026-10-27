"""Knowledge base di LIVEMIND: file markdown in docs/knowledge/**.

Ricerca per parole chiave sulle sezioni (titoli ##/###), senza dipendenze.
Serve al brain (tool `knowledge`) e a qualunque sessione Claude per richiamare
in pochi token la parte giusta: es. search("IRC 4 transient") -> sezione Maximizer.
"""
from __future__ import annotations

import os
import re
import unicodedata

KB_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..",
                                       "docs", "knowledge"))


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def list_topics(kb_dir: str = KB_DIR) -> list[str]:
    """Topic = path relativo senza .md, es. 'mastering/ozone11'."""
    out = []
    for root, _dirs, files in os.walk(kb_dir):
        for f in files:
            if f.endswith(".md"):
                rel = os.path.relpath(os.path.join(root, f), kb_dir)
                out.append(rel[:-3].replace(os.sep, "/"))
    return sorted(out)


def read(topic: str, kb_dir: str = KB_DIR) -> str:
    t = topic.strip().strip("/")
    if t.endswith(".md"):
        t = t[:-3]
    matches = [x for x in list_topics(kb_dir) if x == t or x.endswith("/" + t)]
    if not matches:
        raise FileNotFoundError(f"topic {topic!r} non trovato: {list_topics(kb_dir)}")
    with open(os.path.join(kb_dir, matches[0] + ".md"), encoding="utf-8") as f:
        return f.read()


def sections(topic: str, kb_dir: str = KB_DIR) -> list[tuple[str, str]]:
    """[(titolo, testo)] spezzando su heading ## e ###."""
    text = read(topic, kb_dir)
    parts = re.split(r"(?m)^(#{2,3} .+)$", text)
    out = [("(intro)", parts[0].strip())] if parts[0].strip() else []
    for i in range(1, len(parts), 2):
        out.append((parts[i].lstrip("#").strip(), parts[i + 1].strip()))
    return out


def search(query: str, max_hits: int = 3, kb_dir: str = KB_DIR) -> list[dict]:
    """Sezioni piu' pertinenti con BM25 (termini rari pesano di piu', sezioni lunghe
    non vincono solo per lunghezza); i termini nel titolo valgono doppio."""
    import math
    terms = [t for t in re.findall(r"[\w/+.-]+", _norm(query)) if len(t) > 1]
    if not terms:
        return []
    docs = []
    for topic in list_topics(kb_dir):
        for title, body in sections(topic, kb_dir):
            docs.append((topic, title, body, _norm(title), _norm(body)))
    if not docs:
        return []
    n = len(docs)
    avg = sum(len(d[4]) for d in docs) / n or 1.0
    k1, b = 1.2, 0.75
    idf = {t: math.log(1 + (n - (df := sum(1 for d in docs if t in d[3] or t in d[4]))
                            + 0.5) / (df + 0.5)) for t in terms}
    hits = []
    for topic, title, body, nt, nb in docs:
        score = 0.0
        for t in terms:
            tf = nb.count(t) + 2 * nt.count(t)
            if tf:
                score += idf[t] * tf * (k1 + 1) / (tf + k1 * (1 - b + b * len(nb) / avg))
        if score > 0:
            hits.append({"topic": topic, "section": title, "score": round(score, 3),
                         "text": body})
    hits.sort(key=lambda h: -h["score"])
    return hits[:max_hits]


def dispatch(args: dict) -> str:
    """Entry point del tool `knowledge`."""
    a = args.get("action", "search")
    if a == "topics":
        return "\n".join(list_topics())
    if a == "read":
        return read(args["topic"])
    if a == "search":
        hits = search(args["query"], int(args.get("max_hits", 3)))
        if not hits:
            return "nessun risultato"
        return "\n\n".join(f"### [{h['topic']}] {h['section']}\n{h['text']}" for h in hits)
    if a == "ozone_chain":
        from livemind.mastering.ozone_chains import chain_for, describe
        return describe(chain_for(args["genre"], args.get("destination", "club")))
    if a == "delay_ms":
        from livemind.mastering.ozone_chains import delay_ms
        return f"{delay_ms(float(args['bpm']), args.get('division', '1/4'))} ms"
    return f"azione knowledge sconosciuta: {a}"
