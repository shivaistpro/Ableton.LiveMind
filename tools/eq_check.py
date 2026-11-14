"""Confronta due giri di registrazioni (prima/dopo EQ) e propone il ritocco di volume.

Uso: python eq_check.py <files_prima.json> <files_dopo.json> <ref T1,..> <brani T5,..>
"""
import json
import sys

import numpy as np
import pyloudnorm as pyln

from eq_plan import load, smooth, spec


def main(a_path, b_path, refs, songs):
    A = json.load(open(a_path, encoding="utf-8-sig"))["file"]
    B = json.load(open(b_path, encoding="utf-8-sig"))["file"]
    xa = {k: load(v) for k, v in A.items()}
    xb = {k: load(v) for k, v in B.items()}
    sr = xa[refs[0]][1]
    m = pyln.Meter(sr)
    f = None
    S = {}
    for tag, X in (("a", xa), ("b", xb)):
        for k, (x, _) in X.items():
            f, p = spec(x, sr)
            S[(tag, k)] = smooth(f, p, 1 / 6)
    kk = (f > 60) & (f < 12000)
    r2 = (f > 150) & (f < 8000)
    base = S[("b", refs[0])]
    ref = 10 * np.log10(np.mean([10 ** ((S[("b", r)] - np.mean(S[("b", r)][kk] - base[kk])) / 10) for r in refs], axis=0))
    La = {k: m.integrated_loudness(x) for k, (x, _) in xa.items()}
    Lb = {k: m.integrated_loudness(x) for k, (x, _) in xb.items()}
    ref_l = float(np.mean([Lb[r] for r in refs]))

    def dist(tag, k):
        d = S[(tag, k)] - ref - np.mean(S[(tag, k)][kk] - ref[kk])
        return float(np.sqrt(np.mean(d[r2] ** 2)))
    out = {"ref_lufs": round(ref_l, 2), "brani": {}}
    print("riferimento T1-T4: %.2f LUFS (T1..T4: %s)" % (ref_l, ", ".join("%.1f" % Lb[r] for r in refs)))
    print("brano  LUFS prima -> dopo  | scarto dal rif. | distanza timbrica prima -> dopo | ritocco")
    for s in songs:
        tp = 20 * np.log10(np.abs(xb[s][0]).max() + 1e-12)
        delta = ref_l - Lb[s]
        out["brani"][s] = {"lufs_prima": round(La[s], 2), "lufs_dopo": round(Lb[s], 2), "ritocco_db": round(delta, 1),
                           "dist_prima": round(dist("a", s), 2), "dist_dopo": round(dist("b", s), 2), "picco": round(tp, 1)}
        print("%-5s %6.2f -> %6.2f   | %+5.1f dB        | %.2f -> %.2f                 | %+.1f dB  (picco %.1f dBFS)"
              % (s, La[s], Lb[s], Lb[s] - ref_l, dist("a", s), dist("b", s), delta, tp))
    json.dump(out, open(b_path.replace(".json", "_check.json"), "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3].split(","), sys.argv[4].split(","))
