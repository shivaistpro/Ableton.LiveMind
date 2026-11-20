"""Confronta due giri di registrazioni delle scene piene (prima/dopo master club).

Per brano: LUFS integrato sui ~26 s, short-term max (3 s), true peak (4x),
PLR, livello relativo delle bande (sub 40-60, 2-4 kHz, aria 10-16 kHz) e
"punch" del kick = crest factor (picco/RMS) della banda 40-120 Hz su finestre
di un beat. Se il punch scende di oltre ~1 dB il limiter/clipper sta mangiando
il kick.

Uso: python club_check.py <files_prima.json> <files_dopo.json>
"""
import json
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.signal import butter, resample_poly, sosfiltfilt

BANDS = {"sub40-60": (40, 60), "low60-120": (60, 120), "pres2-4k": (2000, 4000),
         "air10-16k": (10000, 16000)}


def win_path(p):
    """Sotto Linux (sandbox Cowork) i path E:\\CLAUDE SPACE\\... stanno in ~/mnt."""
    import os
    if os.name != "nt" and p[1:3] == ":\\":
        p = os.path.expanduser("~/mnt/" + p[3:].replace("\\", "/"))
    return p


def analyse(path):
    x, sr = sf.read(path, always_2d=True)
    m = pyln.Meter(sr)
    lufs = m.integrated_loudness(x)
    n3 = int(3 * sr)
    st = max(m.integrated_loudness(x[i:i + n3]) for i in range(0, len(x) - n3, sr // 2))
    tp = 20 * np.log10(np.max(np.abs(resample_poly(x, 4, 1, axis=0))) + 1e-12)
    mono = x.mean(axis=1)
    spec = np.abs(np.fft.rfft(mono * np.hanning(len(mono)))) ** 2
    f = np.fft.rfftfreq(len(mono), 1 / sr)
    tot = spec[(f > 20) & (f < 20000)].sum()
    rel = {k: 10 * np.log10(spec[(f >= a) & (f < b)].sum() / tot) for k, (a, b) in BANDS.items()}
    low = sosfiltfilt(butter(4, [40, 120], "bandpass", fs=sr, output="sos"), mono)
    w = int(sr * 60 / 160)                      # ~1 beat a 160 bpm
    cf = [20 * np.log10(np.max(np.abs(s)) / (np.sqrt(np.mean(s ** 2)) + 1e-12))
          for s in (low[i:i + w] for i in range(0, len(low) - w, w))]
    return dict(lufs=lufs, st=st, tp=tp, plr=tp - lufs, punch=float(np.median(cf)), **rel)


def main(a_path, b_path):
    A = json.load(open(a_path, encoding="utf-8-sig"))["file"]
    B = json.load(open(b_path, encoding="utf-8-sig"))["file"]
    keys = ["lufs", "st", "tp", "plr", "punch"] + list(BANDS)
    print("brano " + " ".join("%11s" % k for k in keys))
    out = {}
    for k in A:
        a, b = analyse(win_path(A[k])), analyse(win_path(B[k]))
        out[k] = {"prima": a, "dopo": b}
        print("%-5s " % k + " ".join("%5.1f>%5.1f" % (a[q], b[q]) for q in keys))
    d = {q: np.mean([out[k]["dopo"][q] - out[k]["prima"][q] for k in out]) for q in keys}
    print("media delta: " + ", ".join("%s %+.2f" % (q, v) for q, v in d.items()))
    print("TP max dopo: %.2f dBTP" % max(out[k]["dopo"]["tp"] for k in out))
    return out


if __name__ == "__main__":
    r = main(sys.argv[1], sys.argv[2])
    if len(sys.argv) > 3:
        json.dump(r, open(sys.argv[3], "w"), indent=1)
