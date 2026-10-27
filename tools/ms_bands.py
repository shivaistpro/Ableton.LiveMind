"""Bande Mid e Side (Welch via memmap) per confronto tonale/stereo tra file,
indipendente dal livello: tutto relativo all'energia totale del Mid.
Usage: python ms_bands.py <wav> [<wav> ...]"""
import math, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from measure_big import _header, _dtype
from stem_report import BANDS

def ms_bands(path, nfft=1 << 15, stride=8):
    tag, ch, sr, bits, off, size = _header(path)
    dt, sc = _dtype(tag, bits)
    n = size // (dt.itemsize * ch)
    mm = np.memmap(path, dtype=dt, mode="r", offset=off, shape=(n, ch))
    win = np.hanning(nfft); hop = nfft * stride
    accM = np.zeros(nfft // 2 + 1); accS = np.zeros_like(accM); k = 0
    for s in range(0, n - nfft, hop):
        b = np.asarray(mm[s:s + nfft], dtype=np.float32) / sc
        m = (b[:, 0] + b[:, 1]) * 0.5; sd = (b[:, 0] - b[:, 1]) * 0.5
        accM += np.abs(np.fft.rfft(m * win)) ** 2
        accS += np.abs(np.fft.rfft(sd * win)) ** 2; k += 1
    f = np.fft.rfftfreq(nfft, 1 / sr); totM = accM.sum()
    res = {}
    for name, lo, hi in BANDS:
        mk = (f >= lo) & (f < hi)
        res[name] = (round(10 * math.log10(accM[mk].sum() / totM + 1e-12), 1),
                     round(10 * math.log10(accS[mk].sum() / totM + 1e-12), 1),
                     round(10 * math.log10((accS[mk].sum() + 1e-12) / (accM[mk].sum() + 1e-12)), 1))
    return res, round(n / sr, 1), sr

if __name__ == "__main__":
    for p in sys.argv[1:]:
        r, sec, sr = ms_bands(p)
        print(os.path.basename(p), sec, "s", sr)
        print("  banda   Mid   Side  Side-Mid")
        for k, v in r.items():
            print("  %-7s %6.1f %6.1f %6.1f" % (k, *v))
