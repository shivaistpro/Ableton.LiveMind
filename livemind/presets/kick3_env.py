"""Scrittura delle envelope reali di KICK 3.

Scoperta importante: i <PARAM id="SlotNAmpNodeM_x"> restano a 1.0 anche nei
preset che suonano — sono legacy. Le curve effettive stanno negli elementi

    <SlotN_AmpEnvelope>
      <node x=".." y=".." c=".." isKeytracked="0" isPhaseLocked="0" lockedPhaseValue="0.0"/>
      ...
    </SlotN_AmpEnvelope>

x = tempo normalizzato sulla lunghezza (SlotNAmpEnvMaxLen ms), y = ampiezza
0..1, c = curvatura del segmento (0 = lineare, negativo = concavo/decadimento
piu' rapido all'inizio).
"""
from __future__ import annotations
import re

NODE = ('<node x="{x}" y="{y}" c="{c}" isKeytracked="{kt}" '
        'isPhaseLocked="0" lockedPhaseValue="0.0"/>')


def make_nodes(points, keytracked: int = 0, indent: str = "      ") -> str:
    """points: lista di (x, y) oppure (x, y, curvatura)."""
    out = []
    for p in points:
        x, y = p[0], p[1]
        c = p[2] if len(p) > 2 else 0.0
        out.append(indent + NODE.format(x=x, y=y, c=c, kt=keytracked))
    return "\n".join(out)


def set_envelope(xml: str, tag: str, points, keytracked: int = 0) -> str:
    """Sostituisce il contenuto di <tag>...</tag> con i nodi dati."""
    body = "\n" + make_nodes(points, keytracked) + "\n    "
    pattern = re.compile(r"(<%s>)(.*?)(</%s>)" % (tag, tag), re.S)
    if not pattern.search(xml):
        raise ValueError(f"elemento {tag} assente nel preset")
    return pattern.sub(lambda m: m.group(1) + body + m.group(3), xml, count=1)


def get_envelope(xml: str, tag: str) -> str:
    m = re.search(r"<%s>(.*?)</%s>" % (tag, tag), xml, re.S)
    return m.group(1).strip() if m else ""
