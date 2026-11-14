"""Calcola un EQ prudente per ogni brano rispetto alla media dei brani di riferimento.

Ingresso: registrazioni della scena piu' piena di ogni brano (stesso metodo).
Regole (dalle sessioni T1-T4): solo bande statiche; risonanze strette dove
sporgono dalla propria pendenza; correzione larga solo al 50% della distanza
dalla media e mai oltre 2.5 dB; niente boost sotto 50 Hz; volume del gruppo
per pareggiare la loudness. Ogni proposta viene simulata sulla registrazione.

Uso: python eq_plan.py <status.json con i file> <riferimenti T1,T2,..> <brani T5,..> <out.json>
"""
import json
import sys

import numpy as np
import pyloudnorm as pyln
import scipy.signal as ss
import soundfile as sf

SKIP = 3.0                                     # secondi iniziali (attacco del lancio)


def load(p):
    x, sr = sf.read(p, always_2d=True)
    return x[int(SKIP * sr):], sr


def smooth(f, p, frac):
    lin = 10 ** (p / 10)
    return np.array([10 * np.log10(lin[(f >= c * 2 ** (-frac / 2)) & (f <= c * 2 ** (frac / 2))].mean())
                     if c > 0 else p[0] for c in f])


def spec(x, sr):
    f, p = ss.welch(x.mean(1), sr, nperseg=32768, noverlap=16384)
    return f, 10 * np.log10(p + 1e-20)


def peak(sr, f0, g, q):
    A = 10 ** (g / 40); w = 2 * np.pi * f0 / sr; al = np.sin(w) / (2 * q)
    a0 = 1 + al / A
    return np.array([1 + al * A, -2 * np.cos(w), 1 - al * A]) / a0, np.array([a0, -2 * np.cos(w), 1 - al / A]) / a0


def hshelf(sr, f0, g, q=0.7):
    A = 10 ** (g / 40); w = 2 * np.pi * f0 / sr; al = np.sin(w) / (2 * q); c = np.cos(w)
    b = [A * ((A + 1) + (A - 1) * c + 2 * np.sqrt(A) * al), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - 2 * np.sqrt(A) * al)]
    a = [(A + 1) - (A - 1) * c + 2 * np.sqrt(A) * al, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - 2 * np.sqrt(A) * al]
    return np.array(b) / a[0], np.array(a) / a[0]


def apply(x, sr, bands, gain_db=0.0):
    y = x.copy()
    for b in bands:
        bb, aa = hshelf(sr, b["f"], b["g"], b["q"]) if b["shape"] == "highshelf" else peak(sr, b["f"], b["g"], b["q"])
        y = ss.lfilter(bb, aa, y, axis=0)
    return y * 10 ** (gain_db / 20)


def plan_song(x, sr, f, ref, ref_lufs, meter):
    _, p = spec(x, sr)
    s6, s24, s1 = smooth(f, p, 1 / 6), smooth(f, p, 1 / 24), smooth(f, p, 1.0)
    k = (f > 60) & (f < 12000)
    d = s6 - ref - np.mean(s6[k] - ref[k])                       # distanza dalla media, a pari volume
    bands = []
    # 1) risonanze strette che sporgono dalla propria pendenza (max 3)
    r = s24 - s1
    kk = (f > 100) & (f < 3000)
    pk, prop = ss.find_peaks(r[kk], prominence=4.0)
    cand = sorted(((r[kk][i], f[kk][i]) for i in pk if r[kk][i] > 5.0), reverse=True)[:3]
    for h, fr in cand:
        bands.append({"shape": "bell", "f": round(float(fr)), "g": -round(min(3.5, (h - 2) * 0.5), 1), "q": 6.0})
    # 2) correzione larga verso la media, al 50%, max 2.5 dB
    for c, shape, q in [(60, "bell", 1.0), (125, "bell", 1.0), (250, "bell", 1.0), (500, "bell", 1.0),
                        (1000, "bell", 1.0), (2000, "bell", 1.0), (4000, "bell", 1.0), (9000, "highshelf", 0.7)]:
        sel = (f > c / 2 ** 0.5) & (f < c * 2 ** 0.5)
        dev = float(np.mean(d[sel]))
        if abs(dev) < 3.0:                                       # solo scostamenti evidenti
            continue
        g = -np.sign(dev) * min(abs(dev) * 0.5, 2.0)
        g = min(g, 1.5)                                         # boost prudenti
        if g > 0 and c < 100:
            continue                                            # niente boost di sub
        if any(abs(np.log2(b["f"] / c)) < 0.4 and b["q"] >= 6 for b in bands) and g < 0:
            g = g * 0.5                                         # c'e' gia' una risonanza tagliata li'
        bands.append({"shape": shape, "f": c, "g": round(float(g), 1), "q": q})
    y = apply(x, sr, bands)
    _, py = spec(y, sr)
    sy = smooth(f, py, 1 / 6)
    dy = sy - ref - np.mean(sy[k] - ref[k])
    r2 = (f > 150) & (f < 8000)
    gain = float(np.clip(ref_lufs - meter.integrated_loudness(y), -6, 4))
    return {"bands": bands, "gain_db": round(gain, 1),
            "lufs_prima": round(meter.integrated_loudness(x), 2),
            "lufs_dopo": round(meter.integrated_loudness(apply(x, sr, bands, gain)), 2),
            "distanza_prima": round(float(np.sqrt(np.mean(d[r2] ** 2))), 2),
            "distanza_dopo": round(float(np.sqrt(np.mean(dy[r2] ** 2))), 2)}


def main(status, refs, songs, out):
    files = json.load(open(status, encoding="utf-8-sig"))["file"]
    X = {k: load(v) for k, v in files.items()}
    sr = X[refs[0]][1]
    meter = pyln.Meter(sr)
    specs = {}
    for k, (x, _) in X.items():
        f, p = spec(x, sr)
        specs[k] = smooth(f, p, 1 / 6)
    kk = (f > 60) & (f < 12000)
    base = specs[refs[0]]
    ref = 10 * np.log10(np.mean([10 ** ((specs[r] - np.mean(specs[r][kk] - base[kk])) / 10) for r in refs], axis=0))
    lufs = {k: meter.integrated_loudness(x) for k, (x, _) in X.items()}
    ref_lufs = float(np.mean([lufs[r] for r in refs]))
    res = {"ref_lufs": round(ref_lufs, 2), "lufs": {k: round(v, 2) for k, v in lufs.items()}, "brani": {}}
    for s in songs:
        res["brani"][s] = plan_song(X[s][0], sr, f, ref, ref_lufs, meter)
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2].split(","), sys.argv[3].split(","), sys.argv[4])


