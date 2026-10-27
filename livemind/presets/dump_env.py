"""Stampa gli elementi envelope di un preset KICK 3 (dove stanno le curve vere).

I nodi <PARAM id="SlotNAmpNodeM_x"> risultano tutti a 1.0 anche nei preset che
suonano: le curve effettive vivono negli elementi <SlotN_AmpEnvelope> e
<SlotN_PitchEnvelope>. Questo script serve a leggerli senza aprire il plugin.
"""
from __future__ import annotations
import re
import sys

TAGS = ["Slot1_AmpEnvelope", "Slot1_PitchEnvelope",
        "Slot2_AmpEnvelope", "Slot2_PitchEnvelope"]


def main() -> None:
    path = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 900
    s = open(path, encoding="utf-8").read()
    for tag in TAGS:
        m = re.search(r"<%s>(.*?)</%s>" % (tag, tag), s, re.S)
        body = m.group(1).strip() if m else "ASSENTE"
        print(f"== {tag} == ({len(body)} char)")
        print(body[:limit])
        print()


if __name__ == "__main__":
    main()
