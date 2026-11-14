"""Lancia una scena per brano in Live e registra l'uscita (loopback stereo).

Stesso metodo per tutti i brani, cosi' i confronti di loudness e timbro sono
alla pari. Stato in out/capture_status.json.

Uso: python capture_scenes.py <piano.json> <secondi>
piano.json: [["T5", 28], ["T6", 34], ...]  (etichetta, indice scena)
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import soundcard as sc

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lom_direct import Lom  # noqa: E402
from listen import write_wav_f32  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out", "capture")
STATUS = os.path.join(OUT, "..", "capture_status.json")


def status(**kw):
    with open(STATUS, "w") as f:
        json.dump({**kw, "t": time.strftime("%H:%M:%S")}, f)


def main(plan_path, seconds, sr=48000):
    os.makedirs(OUT, exist_ok=True)
    plan = json.load(open(plan_path))
    lom = Lom(timeout=30)
    if not lom.ping().get("ok"):
        raise SystemExit("Remote Script irraggiungibile")
    spk = sc.default_speaker()
    mic = sc.get_microphone(id=str(spk.name), include_loopback=True)
    for k, (label, scene) in enumerate(plan):
        status(state="lancio", brano=label, scena=scene, fatti=k, totale=len(plan))
        lom.call([], "stop_all_clips")
        time.sleep(2.0)
        lom.call(["scenes:%d" % scene], "fire")
        time.sleep(4.0)                          # quantizzazione di lancio + attacco
        with mic.recorder(samplerate=sr, channels=2) as rec:
            rec.record(numframes=256)
            x = rec.record(numframes=int(seconds * sr))
        write_wav_f32(os.path.join(OUT, "%s.wav" % label), x, sr)
        pk = 20 * np.log10(max(float(np.abs(x).max()), 1e-9))
        status(state="registrato", brano=label, picco=round(pk, 1), fatti=k + 1, totale=len(plan))
    lom.call([], "stop_all_clips")
    lom.call([], "stop_playing")
    status(state="finito", totale=len(plan))


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]))
