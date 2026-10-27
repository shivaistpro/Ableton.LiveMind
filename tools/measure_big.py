"""Measure a WAV too big to load whole (killed stem_report.analyse with
exit 137 / OOM on a 657MB render). Same metrics, computed streaming via
memmap + block accumulation instead of loading the full float array.

Usage: python measure_big.py <wav> [out.json]
"""
from __future__ import annotations
import json
import math
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else ".")
from stem_report import BANDS, db  # reuse the same band table / dB helper


def _header(path):
    with open(path, "rb") as f:
        head = f.read(12)
        if head[:4] != b"RIFF" or head[8:12] != b"WAVE":
            raise ValueError("non e' un file RIFF/WAVE")
        pos = 12
        fmt = data_off = data_size = None
        while True:
            ch = f.read(8)
            if len(ch) < 8:
                break
            cid, size = ch[:4], int.from_bytes(ch[4:8], "little")
            if cid == b"fmt ":
                fmt = f.read(size)
                if size & 1:
                    f.read(1)
            elif cid == b"data":
                data_off = f.tell()
                data_size = size
                break
            else:
                f.seek(size + (size & 1), 1)
        if fmt is None or data_off is None:
            raise ValueError("chunk fmt/data mancante")
    tag = int.from_bytes(fmt[0:2], "little")
    ch_n = int.from_bytes(fmt[2:4], "little")
    sr = int.from_bytes(fmt[4:8], "little")
    bits = int.from_bytes(fmt[14:16], "little")
    if tag == 0xFFFE and len(fmt) >= 26:
        tag = int.from_bytes(fmt[24:26], "little")
    return tag, ch_n, sr, bits, data_off, data_size


def _dtype(tag, bits):
    if tag == 3 and bits == 32:
        return np.dtype("<f4"), 1.0
    if tag == 3 and bits == 64:
        return np.dtype("<f8"), 1.0
    if tag == 1 and bits == 16:
        return np.dtype("<i2"), 32768.0
    if tag == 1 and bits == 32:
        return np.dtype("<i4"), 2147483648.0
    raise ValueError("formato non gestito (24-bit int: usa stem_report su un file piu' piccolo)")


def analyse_big(path, gain_db=0.0, block_frames=2_000_000, fft_stride=8):
    tag, ch_n, sr, bits, data_off, data_size = _header(path)
    dt, scale = _dtype(tag, bits)
    n_frames = data_size // (dt.itemsize * ch_n)
    mm = np.memmap(path, dtype=dt, mode="r", offset=data_off, shape=(n_frames, ch_n))
    g = 10 ** (gain_db / 20.0)

    peak = 0.0
    sum_sq = 0.0
    n_seen = 0
    sum_l2 = sum_r2 = sum_lr = 0.0
    loud_blocks = []
    nfft = 1 << 15
    win = np.hanning(nfft)
    spec_acc = np.zeros(nfft // 2 + 1)
    spec_frames = 0
    carry = np.zeros(0, dtype=np.float32)
    loud_block = int(0.4 * sr)

    for start in range(0, n_frames, block_frames):
        blk = np.asarray(mm[start:start + block_frames], dtype=np.float32) / scale * g
        mono = blk.mean(axis=1) if ch_n >= 2 else blk[:, 0]

        peak = max(peak, float(np.max(np.abs(blk))) if blk.size else 0.0)
        sum_sq += float(np.sum(mono ** 2))
        n_seen += mono.size

        if ch_n >= 2:
            l, r = blk[:, 0], blk[:, 1]
            sum_l2 += float(np.sum(l ** 2))
            sum_r2 += float(np.sum(r ** 2))
            sum_lr += float(np.sum(l * r))

        for i in range(0, mono.size - loud_block + 1, loud_block // 2 or 1):
            seg = mono[i:i + loud_block]
            p = np.mean(seg ** 2)
            if p > 1e-8:
                loud_blocks.append(-0.691 + 10 * math.log10(p))

        cat = np.concatenate([carry, mono]) if carry.size else mono
        pos = 0
        hop = nfft * fft_stride
        while pos + nfft <= cat.size:
            seg = cat[pos:pos + nfft] * win
            spec_acc += np.abs(np.fft.rfft(seg)) ** 2
            spec_frames += 1
            pos += hop
        carry = cat[pos:] if pos < cat.size else np.zeros(0, dtype=np.float32)

    rms = math.sqrt(sum_sq / n_seen) if n_seen else 0.0
    loud_sorted = sorted(loud_blocks)
    gated = [v for v in loud_blocks if v > (loud_sorted[len(loud_sorted) // 2] - 10)] if loud_blocks else []
    lufs = (10 * math.log10(np.mean([10 ** (v / 10) for v in gated]))) if gated else -120.0

    freqs = np.fft.rfftfreq(nfft, 1 / sr)
    total = float(spec_acc.sum()) or 1.0
    bands = {}
    for name, lo, hi in BANDS:
        m = (freqs >= lo) & (freqs < hi)
        bands[name] = round(10 * math.log10(max(float(spec_acc[m].sum()) / total, 1e-9)), 1)
    centroid = float((freqs * spec_acc).sum() / total)
    cumulative = np.cumsum(spec_acc)
    idx = int(np.searchsorted(cumulative, total * 0.5))
    median_f = float(freqs[min(idx, len(freqs) - 1)])
    lowmask = freqs < 200
    peak_low = float(freqs[lowmask][np.argmax(spec_acc[lowmask])]) if lowmask.any() else 0.0

    denom = math.sqrt(sum_l2 * sum_r2)
    corr = (sum_lr / denom) if denom > 0 else 1.0

    return {
        "path": path, "sr": sr, "ch": ch_n, "sec": round(n_frames / sr, 2),
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
        "spec_frames_used": spec_frames,
    }


if __name__ == "__main__":
    r = analyse_big(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else None
    if out:
        json.dump(r, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(r, indent=1, ensure_ascii=False))
