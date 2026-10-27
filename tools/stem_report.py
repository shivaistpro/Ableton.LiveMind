"""Measure the source audio files of a set's tracks, offline.

The tracks in this set are all bounced audio, so their .wav files carry the
exact signal that reaches the mixer. Measuring the files directly gives a
per-track picture (level, peak, crest, spectrum, stereo width, low-end centre)
without rendering or real-time capture.

Usage: python stem_report.py <tracks.json> <out.json>
  tracks.json: [{"name": ..., "path": ..., "gain_db": ...}, ...]
"""
from __future__ import annotations
import json
import math
import sys


import numpy as np


def read_wav(path):
    """Minimal RIFF reader.

    The stdlib `wave` module only handles PCM; Live bounces float32 and
    WAVE_FORMAT_EXTENSIBLE, which it rejects with "unknown format: 3".
    Parsing the chunks directly avoids adding a dependency.
    """
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("non e' un file RIFF/WAVE")
    pos, fmt, audio = 12, None, None
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4]
        size = int.from_bytes(data[pos + 4:pos + 8], "little")
        body = data[pos + 8:pos + 8 + size]
        if cid == b"fmt ":
            fmt = body
        elif cid == b"data":
            audio = body
        pos += 8 + size + (size & 1)
    if fmt is None or audio is None:
        raise ValueError("chunk fmt/data mancante")
    tag = int.from_bytes(fmt[0:2], "little")
    ch = int.from_bytes(fmt[2:4], "little")
    sr = int.from_bytes(fmt[4:8], "little")
    bits = int.from_bytes(fmt[14:16], "little")
    if tag == 0xFFFE and len(fmt) >= 26:          # EXTENSIBLE: real tag in GUID
        tag = int.from_bytes(fmt[24:26], "little")
    if tag == 3 and bits == 32:
        x = np.frombuffer(audio, "<f4")
    elif tag == 3 and bits == 64:
        x = np.frombuffer(audio, "<f8").astype(np.float32)
    elif tag == 1 and bits == 16:
        x = np.frombuffer(audio, "<i2").astype(np.float32) / 32768.0
    elif tag == 1 and bits == 24:
        b = np.frombuffer(audio[:len(audio) // 3 * 3], np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2].astype(np.int8).astype(np.int32) << 16)
        x = v.astype(np.float32) / 8388608.0
    elif tag == 1 and bits == 32:
        x = np.frombuffer(audio, "<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError("formato non gestito: tag=%d bits=%d" % (tag, bits))
    usable = (len(x) // ch) * ch
    return x[:usable].reshape(-1, ch), sr


def db(v):
    return 20.0 * math.log10(v) if v > 1e-9 else -120.0


BANDS = [("sub", 20, 60), ("low", 60, 120), ("lowmid", 120, 300),
         ("mid", 300, 1200), ("himid", 1200, 4000),
         ("hi", 4000, 10000), ("air", 10000, 20000)]


def analyse(path, gain_db=0.0):
    x, sr = read_wav(path)
    g = 10 ** (gain_db / 20.0)
    xg = x * g
    mono = xg.mean(axis=1)

    peak = float(np.max(np.abs(xg))) if xg.size else 0.0
    rms = float(np.sqrt(np.mean(mono ** 2))) if mono.size else 0.0

    # K-weighting is overkill here; RMS-with-gate tracks perceived level well
    # enough to compare stems against each other.
    block = int(0.4 * sr)
    loud = []
    for i in range(0, max(len(mono) - block, 1), block // 2 or 1):
        seg = mono[i:i + block]
        if len(seg) < block // 2:
            break
        p = np.mean(seg ** 2)
        if p > 1e-8:
            loud.append(-0.691 + 10 * math.log10(p))
    loud_sorted = sorted(loud)
    gated = [l for l in loud if l > (loud_sorted[len(loud_sorted) // 2] - 10)] if loud else []
    lufs = (10 * math.log10(np.mean([10 ** (l / 10) for l in gated]))) if gated else -120.0

    # Welch over the whole file: a single FFT on the head only sees the intro,
    # and on an arrangement the kick often enters bars later.
    nfft = 1 << 15
    if len(mono) >= nfft:
        win = np.hanning(nfft)
        hop = nfft
        acc = np.zeros(nfft // 2 + 1)
        frames = 0
        for i in range(0, len(mono) - nfft + 1, hop):
            seg = mono[i:i + nfft] * win
            acc += np.abs(np.fft.rfft(seg)) ** 2
            frames += 1
        spec = acc / max(frames, 1)
        freqs = np.fft.rfftfreq(nfft, 1 / sr)
        total = float(spec.sum()) or 1.0
        bands = {}
        for name, lo, hi in BANDS:
            m = (freqs >= lo) & (freqs < hi)
            bands[name] = round(10 * math.log10(max(float(spec[m].sum()) / total, 1e-9)), 1)
        centroid = float((freqs * spec).sum() / total)
        cumulative = np.cumsum(spec)
        idx = int(np.searchsorted(cumulative, total * 0.5))
        median_f = float(freqs[min(idx, len(freqs) - 1)])
        lowmask = freqs < 200
        peak_low = float(freqs[lowmask][np.argmax(spec[lowmask])]) if lowmask.any() else 0.0
    else:
        bands, centroid, median_f, peak_low = {}, 0.0, 0.0, 0.0

    if xg.shape[1] >= 2:
        l, r = xg[:, 0], xg[:, 1]
        denom = math.sqrt(float(np.sum(l ** 2)) * float(np.sum(r ** 2)))
        corr = float(np.sum(l * r) / denom) if denom > 0 else 1.0
    else:
        corr = 1.0

    return {
        "path": path, "sr": sr, "ch": int(x.shape[1]),
        "sec": round(len(x) / sr, 2),
        "gain_db": gain_db,
        "peak_db": round(db(peak), 2),
        "rms_db": round(db(rms), 2),
        "lufs": round(lufs, 2),
        "crest_db": round(db(peak) - db(rms), 2),
        "corr": round(corr, 3),
        "centroid_hz": round(centroid),
        "median_hz": round(median_f),
        "low_peak_hz": round(peak_low, 1),
        "bands_db": bands,
    }


def main(tracks_path, out_path):
    tracks = json.load(open(tracks_path, encoding="utf-8"))
    res = []
    for t in tracks:
        try:
            r = analyse(t["path"], t.get("gain_db", 0.0))
        except Exception as e:
            r = {"path": t["path"], "error": str(e)}
        r["name"] = t["name"]
        res.append(r)
        print("%-30s peak%7s  lufs%7s  crest%6s  corr%6s  lowpk%7s Hz"
              % (t["name"][:30], r.get("peak_db"), r.get("lufs"),
                 r.get("crest_db"), r.get("corr"), r.get("low_peak_hz")))
    json.dump(res, open(out_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("-> " + out_path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
