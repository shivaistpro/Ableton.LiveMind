"""Mixer di Live via LOM diretto: report di volumi/solo/mute/catene e gain in dB.

Sostituisce i vecchi script legati a un singolo set (indici di traccia fissi):
qui le tracce si indicano per NOME (o indice) e nessun dato del progetto e'
scritto nel codice.

    python mixer.py report                 # tutte le tracce: dB, solo, mute
    python mixer.py report --chains        # + device di ogni traccia (lento su set grandi)
    python mixer.py report --filter bus    # solo tracce il cui nome contiene "bus"
    python mixer.py set gains.json         # {"KICK BUS": -9, "12": -6.5, "MASTER": 0}

Il fader di Live NON e' lineare in ampiezza (0.85 = 0 dB, 1.0 = +6 dB): il valore
giusto per un dato dB si trova chiedendo a Live la sua stessa etichetta
(`str_for_value`) e bisecando. `set` rifiuta gain sopra 0 dB e rilegge il valore.
Output JSON anche in LIVEMIND/out/.
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lom_direct import Lom  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
MASTER = "MASTER"


def parse_db(label) -> float | None:
    """'-6.0 dB' -> -6.0 ; '-inf dB' -> -inf ; altro -> None."""
    if not isinstance(label, str):
        return None
    s = label.strip().lower()
    if s.startswith("-inf"):
        return float("-inf")
    m = re.match(r"^([+-]?\d+(?:\.\d+)?)", s)
    return float(m.group(1)) if m else None


def value_for_db(target_db: float, db_of, lo=0.0, hi=1.0, steps=24) -> float:
    """Bisezione su una funzione monotona crescente value->dB (quella di Live)."""
    for _ in range(steps):
        mid = (lo + hi) / 2
        d = db_of(mid)
        if d is None:
            raise RuntimeError("Live non restituisce l'etichetta in dB del fader")
        if d < target_db:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 6)


def _vol_path(idx) -> list:
    return (["master_track"] if idx == MASTER else ["tracks:%d" % idx]) + ["mixer_device", "volume"]


def _db_of(lom: Lom, idx):
    def f(v):
        r = lom.call(_vol_path(idx), "str_for_value", [v])
        return parse_db(r.get("value")) if r.get("ok") else None
    return f


def track_names(lom: Lom) -> list[str]:
    n = lom.length(["tracks"]) or 0
    return [lom.get(["tracks:%d" % i], "name") or "" for i in range(n)]


def resolve(key: str, names: list[str]):
    """'MASTER', indice numerico o nome esatto (case-insensitive) -> indice."""
    if key.strip().upper() == MASTER:
        return MASTER
    if key.strip().isdigit():
        return int(key)
    hits = [i for i, n in enumerate(names) if n.strip().lower() == key.strip().lower()]
    if len(hits) != 1:
        raise KeyError("traccia %r: %s" % (key, "non trovata" if not hits else "nome ambiguo %s" % hits))
    return hits[0]


def report(lom: Lom, chains=False, name_filter=None) -> list[dict]:
    rows = []
    names = track_names(lom)
    for i, name in list(enumerate(names)) + [(MASTER, MASTER)]:
        if name_filter and name_filter.lower() not in name.lower() and i != MASTER:
            continue
        base = ["master_track"] if i == MASTER else ["tracks:%d" % i]
        vol = lom.get(_vol_path(i), "value")
        row = {"idx": i, "nome": name,
               "db": parse_db(lom.call(_vol_path(i), "str_for_value", [vol]).get("value"))
               if vol is not None else None}
        if i != MASTER:
            row["solo"] = lom.get(base, "solo")
            row["mute"] = lom.get(base, "mute")
        if chains:
            n = lom.length(base + ["devices"]) or 0
            row["devices"] = [{"nome": lom.get(base + ["devices:%d" % d], "name"),
                               "attivo": lom.get(base + ["devices:%d" % d], "is_active")}
                              for d in range(n)]
        rows.append(row)
    return rows


def set_gains(lom: Lom, gains: dict) -> dict:
    names = track_names(lom)
    out = {}
    for key, db in gains.items():
        db = float(db)
        if db > 0.0001:
            out[key] = {"errore": "%.1f dB supera 0 dB: rifiutato" % db}
            continue
        idx = resolve(str(key), names)
        f = _db_of(lom, idx)
        v = value_for_db(db, f)
        r = lom.set(_vol_path(idx), "value", v)
        got = lom.get(_vol_path(idx), "value")
        out[key] = {"idx": idx, "db_voluto": db, "set_ok": r.get("ok"),
                    "db_letto": f(got) if got is not None else None}
    return out


def group_tracks(lom: Lom) -> list[tuple[int, str]]:
    """Tracce gruppo del set (is_foldable): [(indice, nome)]. Niente indici fissi."""
    n = lom.length(["tracks"]) or 0
    return [(i, lom.get(["tracks:%d" % i], "name")) for i in range(n)
            if lom.get(["tracks:%d" % i], "is_foldable")]


def find_device(lom: Lom, track_path: list, name: str | None = None,
                class_name: str | None = None) -> list:
    """Path del primo device per nome (sottostringa, case-insensitive) o class_name."""
    for d in range(lom.length(track_path + ["devices"]) or 0):
        p = track_path + ["devices:%d" % d]
        if (name and name.lower() in str(lom.get(p, "name")).lower()) or \
           (class_name and lom.get(p, "class_name") == class_name):
            return p
    raise SystemExit("device non trovato su %s: %s" % (track_path, name or class_name))


def find_param(lom: Lom, dev_path: list, name: str) -> list:
    """Path del parametro per nome: prima match esatto, poi sottostringa."""
    names = [str(lom.get(dev_path + ["parameters:%d" % j], "name"))
             for j in range(lom.length(dev_path + ["parameters"]) or 0)]
    for test in (lambda x: x.lower() == name.lower(), lambda x: name.lower() in x.lower()):
        for j, x in enumerate(names):
            if test(x):
                return dev_path + ["parameters:%d" % j]
    raise SystemExit("parametro %r non trovato in %s" % (name, names))


def _dump(name: str, data) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False, default=str)
    print(json.dumps(data, ensure_ascii=False, default=str))


def main(argv):
    lom = Lom(timeout=5)
    if not argv or argv[0] not in ("report", "set"):
        raise SystemExit(__doc__)
    if argv[0] == "report":
        filt = argv[argv.index("--filter") + 1] if "--filter" in argv else None
        rows = report(lom, chains="--chains" in argv, name_filter=filt)
        soli = [r["nome"] for r in rows if r.get("solo")]
        if soli:
            print("ATTENZIONE, tracce in SOLO (zittiscono tutto il resto):", soli)
        _dump("mixer_report.json", rows)
    else:
        with open(argv[1], encoding="utf-8") as fh:
            _dump("mixer_set_result.json", set_gains(lom, json.load(fh)))


if __name__ == "__main__":
    main(sys.argv[1:])
