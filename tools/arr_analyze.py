"""Analyse a full-arrangement capture section by section (start -> end).

A single integrated number hides where a mix breaks: the drop can clip while
the intro is 10 LU down, the low end can go wide only in the break. This cuts
the capture into blocks of N bars (aligned to the song grid) and measures each:

  - LUFS short-term/momentary max, BS.1770-4 K-weighted (pyloudnorm)
  - true peak dBTP (4x oversampled, polyphase) and sample peak
  - PLR (true peak - short-term loudness) and crest
  - 7-band balance, mid/side ratio per band, L/R correlation (full & <150 Hz)
  - which tracks have clips in that block (from als_scan.py JSON), so every
    number points at the parts that cause it

Also writes a timeline PNG (loudness, peaks, bands, stereo) to LOOK at.

Usage:
  python arr_analyze.py <capture.wav> <bpm> [start_beat] [bars_per_block]
                        [als_scan.json] [out_prefix]
Needs: numpy scipy pyloudnorm matplotlib
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
import pyloudnorm as pyln
from scipy import signal

sys.path.insert(0, os.path.dirname(__file__))
from stem_report import read_wav  # noqa: E402

BANDS = [("sub", 20, 60), ("low", 60, 120), ("lowmid", 120, 300),
         ("mid", 300, 1200), ("himid", 1200, 4000),
         ("hi", 4000, 10000), ("air", 10000, 20000)]


def db(v, floor=-120.0):
    return 20 * math.log10(v) if v > 1e-12 else floor


def true_peak(x, os_factor=4):
    y = signal.resample_poly(x, os_factor, 1, axis=0)
    return float(np.max(np.abs(y))) if y.size else 0.0


def band_stats(x, sr):
    """Energy per band (dB rel. total), side/mid ratio per band (dB)."""
    mid = (x[:, 0] + x[:, 1]) * 0.5
    side = (x[:, 0] - x[:, 1]) * 0.5
    f, pm = signal.welch(mid, sr, nperseg=8192)
    _, ps = signal.welch(side, sr, nperseg=8192)
    tot = float(pm.sum() + ps.sum()) or 1e-20
    out, ms = {}, {}
    for name, lo, hi in BANDS:
        m = (f >= lo) & (f < hi)
        e_m, e_s = float(pm[m].sum()), float(ps[m].sum())
        out[name] = round(10 * math.log10(max((e_m + e_s) / tot, 1e-12)), 1)
        ms[name] = round(10 * math.log10(max(e_s, 1e-20) / max(e_m, 1e-20)), 1)
    return out, ms, f, pm + ps


def corr(l, r):
    d = math.sqrt(float(np.sum(l * l)) * float(np.sum(r * r)))
    return float(np.sum(l * r) / d) if d > 0 else 1.0


def active_tracks(scan, b0, b1):
    if not scan:
        return []
    names = []
    for t in scan["tracks"]:
        for c in t.get("clips") or []:
            if c.get("start", 0) < b1 and c.get("end", 0) > b0 and not c.get("disabled"):
                names.append(t["name"])
                break
    return names


def main(path, bpm, start_beat=0.0, bars=8, scan_path=None, prefix=None):
    x, sr = read_wav(path)
    x = x.astype(np.float64)
    scan = json.load(open(scan_path)) if scan_path else None
    meter = pyln.Meter(sr)                     # BS.1770-4, 400 ms / 75 % overlap
    st_meter = pyln.Meter(sr, block_size=3.0)  # short-term

    # trim leading silence of the capture (stream start latency) to align grid
    env = np.max(np.abs(x), axis=1)
    first = int(np.argmax(env > 1e-4)) if np.any(env > 1e-4) else 0
    # trim trailing silence too: the capture runs a fixed length, the song
    # may be stopped earlier by hand — a silent tail would drag every
    # integrated number down and add empty blocks
    env = env[first:]
    loud_idx = np.nonzero(env > 1e-3)[0]            # -60 dBFS
    last = int(loud_idx[-1]) + 1 if loud_idx.size else len(env)
    x = x[first:first + last]
    spb = 60.0 / bpm
    block_s = bars * 4 * spb
    n_blocks = int(math.ceil(len(x) / sr / block_s))

    lp = signal.butter(4, 150, "low", fs=sr, output="sos")
    xl = signal.sosfiltfilt(lp, x, axis=0)

    blocks = []
    for b in range(n_blocks):
        i0, i1 = int(b * block_s * sr), int(min((b + 1) * block_s * sr, len(x)))
        seg = x[i0:i1]
        if len(seg) < sr * 3.1:
            continue
        beat0 = start_beat + b * bars * 4
        rms = float(np.sqrt(np.mean(seg ** 2)))
        if rms < 1e-5:
            blocks.append({"block": b, "bar": int(beat0 // 4) + 1, "silent": True})
            continue
        lufs_st = st_meter.integrated_loudness(seg)
        # momentary max over 400 ms windows
        w = int(0.4 * sr)
        mom = [meter.integrated_loudness(seg[k:k + w]) for k in range(0, len(seg) - w, w)]
        mom = [m for m in mom if np.isfinite(m)]
        tp = true_peak(seg)
        sp = float(np.max(np.abs(seg)))
        bands, ms, _, _ = band_stats(seg, sr)
        blk = {
            "block": b, "bar": int(beat0 // 4) + 1, "beat": beat0,
            "time": round(i0 / sr, 1),
            "lufs_st": round(lufs_st, 1),
            "lufs_mom_max": round(max(mom), 1) if mom else None,
            "tp_dbtp": round(db(tp), 2), "sample_peak_db": round(db(sp), 2),
            "plr": round(db(tp) - lufs_st, 1),
            "crest": round(db(sp) - db(rms), 1),
            "corr": round(corr(seg[:, 0], seg[:, 1]), 3),
            "corr_low": round(corr(xl[i0:i1, 0], xl[i0:i1, 1]), 3),
            "bands": bands, "side_mid_db": ms,
            "tracks": active_tracks(scan, beat0, beat0 + bars * 4),
        }
        blocks.append(blk)

    # whole-song
    integ = meter.integrated_loudness(x)
    tp_all = true_peak(x)
    bands_all, ms_all, f, p = band_stats(x, sr)
    lra = None
    try:
        lra = round(meter.loudness_range(x), 1) if hasattr(meter, "loudness_range") else None
    except Exception:
        lra = None
    live = [b for b in blocks if not b.get("silent")]
    summary = {
        "file": path, "sr": sr, "sec": round(len(x) / sr, 1), "bpm": bpm,
        "bars_per_block": bars, "lead_trim_s": round(first / sr, 3), "music_end_s": round(len(x) / sr, 1),
        "lufs_integrated": round(integ, 2), "tp_dbtp": round(db(tp_all), 2),
        "sample_peak_db": round(db(float(np.max(np.abs(x)))), 2),
        "lra": lra, "plr": round(db(tp_all) - integ, 1),
        "corr": round(corr(x[:, 0], x[:, 1]), 3),
        "corr_low": round(corr(xl[:, 0], xl[:, 1]), 3),
        "bands": bands_all, "side_mid_db": ms_all,
        "loudest_block": max(live, key=lambda b: b["lufs_st"])["bar"] if live else None,
        "hottest_tp_block": max(live, key=lambda b: b["tp_dbtp"])["bar"] if live else None,
        "headroom_to_-6dBTP": round(-6.0 - db(tp_all), 2),
    }
    prefix = prefix or os.path.splitext(path)[0] + "_arr"
    with open(prefix + ".json", "w") as fjs:
        json.dump({"summary": summary, "blocks": blocks}, fjs, indent=1)
    plot(x, sr, blocks, summary, f, p, prefix + ".png")
    print(json.dumps(summary, indent=1))
    return summary, blocks


def plot(x, sr, blocks, s, f, p, png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    live = [b for b in blocks if not b.get("silent")]
    bars = [b["bar"] for b in live]
    fig, ax = plt.subplots(5, 1, figsize=(16, 17), gridspec_kw={"height_ratios": [1.2, 1, 1.2, 1, 1.6]})
    t = np.arange(len(x)) / sr
    step = max(1, len(x) // 20000)
    ax[0].plot(t[::step], x[::step, 0], lw=0.3, color="#4a78c2")
    ax[0].plot(t[::step], -x[::step, 1], lw=0.3, color="#c26a4a")
    ax[0].axhline(10 ** (-6 / 20), color="r", ls="--", lw=0.8)
    ax[0].axhline(-(10 ** (-6 / 20)), color="r", ls="--", lw=0.8)
    ax[0].set_title("Forma d'onda L (su) / R (giu', invertita) — linee rosse = -6 dBFS  |  "
                    "integr. %.1f LUFS  TP %.1f dBTP  PLR %.1f  corr %.2f  corr<150Hz %.2f"
                    % (s["lufs_integrated"], s["tp_dbtp"], s["plr"], s["corr"], s["corr_low"]))
    ax[0].set_xlabel("s")
    ax[1].plot(bars, [b["lufs_st"] for b in live], "o-", label="LUFS short-term (blocco)")
    ax[1].plot(bars, [b["lufs_mom_max"] for b in live], "x--", label="LUFS momentary max")
    ax[1].plot(bars, [b["tp_dbtp"] for b in live], "s-", color="r", label="True peak dBTP")
    ax[1].axhline(-6, color="r", ls=":", lw=1)
    ax[1].set_ylabel("dB"); ax[1].legend(fontsize=8); ax[1].grid(alpha=.3); ax[1].set_xlabel("battuta")
    for name, _, _ in BANDS:
        ax[2].plot(bars, [b["bands"][name] for b in live], "-", label=name)
    ax[2].set_title("Bilanciamento per banda (dB rel. totale del blocco)")
    ax[2].legend(fontsize=8, ncol=7); ax[2].grid(alpha=.3)
    for name, _, _ in BANDS:
        ax[3].plot(bars, [b["side_mid_db"][name] for b in live], "-", label=name)
    ax[3].plot(bars, [10 * math.log10(max(1e-6, 1 - b["corr_low"])) for b in live], "k:", label="10log(1-corr<150)")
    ax[3].set_title("Side/Mid per banda (dB) — sotto -20 dB = mono di fatto")
    ax[3].legend(fontsize=8, ncol=8); ax[3].grid(alpha=.3)
    mono = x.mean(axis=1)
    ff, tt, S = signal.spectrogram(mono, sr, nperseg=4096, noverlap=2048)
    S = 10 * np.log10(S + 1e-14)
    ax[4].pcolormesh(tt, ff, S, shading="auto", cmap="magma", vmin=S.max() - 90, vmax=S.max())
    ax[4].set_yscale("symlog", linthresh=100); ax[4].set_ylim(20, sr / 2)
    ax[4].set_title("Spettrogramma (mono)"); ax[4].set_xlabel("s"); ax[4].set_ylabel("Hz")
    fig.tight_layout(); fig.savefig(png, dpi=80); plt.close(fig)


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        raise SystemExit(__doc__)
    main(a[0], float(a[1]), float(a[2]) if len(a) > 2 else 0.0,
         int(a[3]) if len(a) > 3 else 8, a[4] if len(a) > 4 else None,
         a[5] if len(a) > 5 else None)
