"""Stem per ogni traccia gruppo del set (rilevate via LOM) via solo + loopback (niente dialogo Esporta, niente UI).
Per ogni gruppo: solo -> cattura N s dal beat dato -> unsolo. Sempre unsolo in finally.
Usage: python stem_listen.py [secondi=30] [beat=400]   -> out/STEM_<nome>.wav, out/stem_listen_status.json"""
import os, sys  # noqa: E401
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _paths import OUT, SHOTS, out_path  # noqa: E402,F401
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lom_direct import Lom
import listen
import mixer

OUT = str(OUT)

def st(**kw):
    with open(os.path.join(OUT, "stem_listen_status.json"), "w") as f:
        json.dump(kw, f)

def main(sec=30.0, beat=400.0):
    lom = Lom()
    if not lom.ping().get("ok"):
        st(state="error", why="LOM"); return
    groups = mixer.group_tracks(lom)
    done = []
    try:
        for idx, name in groups:
            for i, _ in groups:
                lom.set(["tracks:%d" % i], "solo", i == idx)
            time.sleep(0.5)
            st(state="running", now=name, done=done)
            listen.main(sec, "STEM_" + name, beat)
            done.append(name)
    finally:
        for i, _ in groups:
            lom.set(["tracks:%d" % i], "solo", False)
        st(state="done", done=done)

if __name__ == "__main__":
    a = sys.argv[1:]
    main(float(a[0]) if a else 30.0, float(a[1]) if len(a) > 1 else 400.0)
