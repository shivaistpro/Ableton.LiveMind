"""Inietta preset Pro-Q 3 (e opzionalmente gain) in un set .als, offline, da un piano JSON.

Versione generica dei vecchi script legati a un singolo progetto: nessun path,
nome di traccia o preset e' scritto nel codice, tutto arriva dal piano.

    python inject_eq_plan.py <set.als> <piano.json> [out.als]

piano.json:
    {
      "preset_dir": "~/Documents/FabFilter/Presets/Pro-Q 3/<cartella>",
      "eq":    {"KICK BUS": "BUS KICK", "12": "SYNTH LOW", "MASTER": "MASTER CORR"},
      "gains_db": {"KICK BUS": -9.0}
    }

- chiavi = nome traccia esatto (case-insensitive), indice, oppure "MASTER";
- valori di "eq" = nome del preset .ffp (senza estensione) in preset_dir, o path completo;
- "gains_db" facoltativo: volume del fader in dB (nel .als e' lineare, 1.0 = 0 dB),
  rifiutato se sopra 0 dB.
Serve almeno un Pro-Q 3 gia' presente nel set (fa da modello XML). Di default scrive
un NUOVO file "<set> LIVEMIND.als" accanto all'originale; per sovrascrivere passare
lo stesso path come out.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import als_device as A  # noqa: E402


def resolve(key: str, names: list[str]) -> int:
    """'MASTER' -> -1, indice numerico, o nome esatto (case-insensitive)."""
    k = key.strip()
    if k.upper() == "MASTER":
        return -1
    if k.isdigit():
        return int(k)
    hits = [i for i, n in enumerate(names) if n.strip().lower() == k.lower()]
    if len(hits) != 1:
        raise KeyError("traccia %r: %s" % (key, "non trovata" if not hits else "nome ambiguo %s" % hits))
    return hits[0]


def preset_path(value: str, preset_dir: str | None) -> str:
    p = value if value.lower().endswith(".ffp") or os.path.isabs(value) else \
        os.path.join(os.path.expanduser(preset_dir or ""), value + ".ffp")
    if not os.path.isfile(p):
        raise FileNotFoundError("preset non trovato: %s" % p)
    return p


def main(src: str, plan_path: str, dst: str | None = None) -> str:
    with open(plan_path, encoding="utf-8") as fh:
        plan = json.load(fh)
    dst = dst or os.path.splitext(src)[0] + " LIVEMIND.als"
    tree = A.load(src)
    root = tree.getroot()
    tracks = list(root.find("LiveSet/Tracks"))
    names = [A.track_name(t) for t in tracks]

    eq = plan.get("eq", {})
    if eq:
        template = A.find_template(root)
        if template is None:
            raise SystemExit("nessun Pro-Q 3 nel set: caricane uno a mano come modello XML")
        for key, preset in eq.items():
            idx = resolve(key, names)
            path = preset_path(preset, plan.get("preset_dir"))
            A.strip_proq3(root, idx)
            A.add_proq3(root, idx, path, os.path.splitext(os.path.basename(path))[0], template)
            print("  EQ   %-26s <- %s" % ("MASTER" if idx < 0 else names[idx][:26], path))

    for key, db in plan.get("gains_db", {}).items():
        if float(db) > 0.0001:
            raise SystemExit("gain %s dB su %r supera 0 dB: rifiutato" % (db, key))
        idx = resolve(key, names)
        old = A.set_volume(root, idx, float(db))
        print("  GAIN %-26s %s -> %+.1f dB" % ("MASTER" if idx < 0 else names[idx][:26], old, float(db)))

    A.save(tree, dst)
    print("scritto:", dst)
    return dst


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
