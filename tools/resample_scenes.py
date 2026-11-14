"""Registra dentro Live (traccia armata in Resampling) la scena piu' piena di
ogni brano. Funziona anche con driver ASIO, dove il loopback di Windows e' muto.

Uso: python resample_scenes.py <piano.json> <indice traccia rec> <secondi>
Stato e percorsi dei file registrati: out/resample_status.json
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lom_direct import Lom  # noqa: E402

STATUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out", "resample_status.json")


def main(plan_path, rec, seconds):
    plan = json.load(open(plan_path))
    lom = Lom(timeout=60)
    files = {}
    for k, (label, scene) in enumerate(plan):
        json.dump({"state": "registro", "brano": label, "fatti": k, "file": files}, open(STATUS, "w"))
        lom.call([], "stop_all_clips")
        time.sleep(2.5)
        slot = ["tracks:%d" % rec, "clip_slots:%d" % scene]
        lom.call(["scenes:%d" % scene], "fire")
        time.sleep(0.4)
        if not lom.get(slot, "is_recording") and not lom.get(slot, "has_clip"):
            lom.call(slot, "fire")
        time.sleep(seconds)
        lom.call([], "stop_all_clips")
        time.sleep(2.0)
        files[label] = lom.get(slot + ["clip"], "file_path")
    lom.call([], "stop_playing")
    json.dump({"state": "finito", "file": files}, open(STATUS, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), float(sys.argv[3]))
