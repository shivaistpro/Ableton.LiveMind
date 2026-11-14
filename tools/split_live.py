"""Divide in Live, via LOM, le tracce che hanno clip in piu' brani.

Per ogni traccia condivisa: duplicate_track tante volte quanti sono i brani,
poi ogni copia tiene solo le clip delle scene del suo brano e viene rinominata
"<nome> [Tn]". Nessun gruppo spostato, nessun device o volume toccato: la
copia e' identica all'originale, solo con meno clip.

Il piano si calcola dal .als (stesso set aperto in Live) e prima di toccare
qualcosa si verifica via LOM che nomi e clip coincidano.

Uso:  python split_live.py <set.als> plan|run
Stato: out/split_live_status.json
"""
from __future__ import annotations

import gzip
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lom_direct import Lom  # noqa: E402

SONGS = [("T1", 0, 7), ("T2", 8, 12), ("T3", 13, 20), ("T4", 21, 24),
         ("T5", 25, 31), ("T6", 32, 37), ("T7", 38, 42), ("T8", 43, 46),
         ("T9", 47, 52), ("T10", 53, 63), ("T11", 64, 71)]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
STATUS = os.path.join(OUT, "split_live_status.json")


def song_of(scene):
    for label, lo, hi in SONGS:
        if lo <= scene <= hi:
            return label
    return None


def plan(als):
    """[{index, name, songs: [(label, [scene...]), ...]}] in ordine di indice."""
    ls = ET.parse(gzip.open(als)).getroot().find("LiveSet")
    tracks = [t for t in ls.find("Tracks") if t.tag != "ReturnTrack"]
    out = []
    for i, t in enumerate(tracks):
        if t.tag == "GroupTrack":
            continue
        by = {}
        for k, cs in enumerate(t.findall("DeviceChain/MainSequencer/ClipSlotList/ClipSlot")):
            if cs.find("ClipSlot/Value/AudioClip") is None and cs.find("ClipSlot/Value/MidiClip") is None:
                continue
            s = song_of(k)
            if s is None:
                raise SystemExit("clip fuori da ogni brano: traccia %d scena %d" % (i, k))
            by.setdefault(s, []).append(k)
        if len(by) > 1:
            order = [s for s, _, _ in SONGS if s in by]
            out.append({"index": i, "name": t.find("Name/EffectiveName").get("Value"),
                        "songs": [(s, by[s]) for s in order]})
    return out


def status(state, **kw):
    os.makedirs(OUT, exist_ok=True)
    with open(STATUS, "w", encoding="utf-8") as f:
        json.dump({"state": state, "t": time.strftime("%H:%M:%S"), **kw}, f, ensure_ascii=False, indent=1)


def call(path, method, args=None):
    c = {"cmd": "call", "root": "song", "path": path, "method": method}
    if args is not None:                  # args vuoto fa fallire la chiamata: si omette
        c["args"] = args
    return c


def get(path, prop):
    return {"cmd": "get", "root": "song", "path": path, "prop": prop}


def batch(lom, cmds):
    r = lom.send({"cmd": "batch", "cmds": cmds})
    if not r.get("ok"):
        raise RuntimeError("batch fallito: %s" % r)
    return r["value"]


def verify_start(lom, p):
    """Prima di toccare qualcosa: nomi e clip in Live devono coincidere col piano."""
    for item in p:
        i = item["index"]
        scenes = sorted(s for _, ss in item["songs"] for s in ss)
        res = batch(lom, [get(["tracks:%d" % i], "name")] +
                    [get(["tracks:%d" % i, "clip_slots:%d" % s], "has_clip") for s in scenes])
        name = res[0].get("value")
        if name != item["name"] or not all(r.get("value") for r in res[1:]):
            raise SystemExit("Live non coincide col piano alla traccia %d: %r vs %r" % (i, name, item["name"]))


def base_name(n):
    return re.sub(r"^\d+[ -]", "", n)


def run(lom, p):
    done = []
    for item in sorted(p, key=lambda x: -x["index"]):   # dal basso: gli indici sopra restano validi
        i, songs = item["index"], item["songs"]
        status("lavoro", traccia=item["name"], fatte=len(done), totale=len(p))
        for _ in range(len(songs) - 1):
            r = lom.send(call([], "duplicate_track", [i]))
            if not r.get("ok"):
                raise RuntimeError("duplicate_track %d: %s" % (i, r))
        all_sc = [s for _, ss in songs for s in ss]
        for m, (label, keep) in enumerate(songs):
            ti = i + m
            drop = [s for s in all_sc if s not in keep]
            cmds = [call(["tracks:%d" % ti, "clip_slots:%d" % s], "delete_clip") for s in drop]
            cmds.append({"cmd": "set", "root": "song", "path": ["tracks:%d" % ti], "prop": "name",
                         "value": "%s [%s]" % (base_name(item["name"]), label)})
            batch(lom, cmds)
            chk = batch(lom, [get(["tracks:%d" % ti, "clip_slots:%d" % s], "has_clip") for s in all_sc])
            got = [s for s, r in zip(all_sc, chk) if r.get("value")]
            if sorted(got) != sorted(keep):
                raise RuntimeError("verifica fallita traccia %d (%s): clip %s, attese %s" % (ti, label, got, keep))
        done.append(item["name"])
    return done


if __name__ == "__main__":
    als, mode = sys.argv[1], sys.argv[2]
    p = plan(als)
    if mode == "plan":
        for it in p:
            print("%4d %-40s %s" % (it["index"], it["name"][:40], " ".join("%s:%s" % (s, sc) for s, sc in it["songs"])))
        print("tracce da dividere: %d, copie nuove: %d" % (len(p), sum(len(x["songs"]) - 1 for x in p)))
        sys.exit(0)
    import pygetwindow as gw  # guardia: mai lavorare su un set diverso dalla copia
    titles = [w.title for w in gw.getAllWindows() if " - Ableton Live" in (w.title or "")]
    if not any(os.path.splitext(os.path.basename(als))[0] in t for t in titles):
        raise SystemExit("in Live non e' aperto il set atteso: %s" % titles)
    lom = Lom(timeout=60)
    try:
        status("verifica")
        verify_start(lom, p)
        done = run(lom, p)
        status("finito", tracce=len(done), copie=sum(len(x["songs"]) - 1 for x in p))
        print("finito:", len(done))
    except BaseException as e:
        status("errore", errore=str(e))
        raise

