"""Render waveform + log spectrogram of a WAV, to be looked at.

Numbers said "no bass at all" — an image tells immediately whether that is a
mix problem, a capture problem, or plain noise.
"""
from __future__ import annotations

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402
import numpy as np                # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stem_report import read_wav  # noqa: E402


def main(src, dst=None):
    x, sr = read_wav(src)
    mono = x.mean(axis=1)
    dst = dst or os.path.splitext(src)[0] + "_spec.png"

    fig, ax = plt.subplots(2, 1, figsize=(12, 7), height_ratios=[1, 2])
    t = np.arange(len(mono)) / sr
    ax[0].plot(t, mono, lw=0.4, color="#d08050")
    ax[0].set_xlim(0, t[-1] if len(t) else 1)
    ax[0].set_ylabel("ampiezza")
    ax[0].set_title(os.path.basename(src))

    nfft, hop = 2048, 512
    frames = max((len(mono) - nfft) // hop, 1)
    S = np.empty((nfft // 2 + 1, frames))
    win = np.hanning(nfft)
    for i in range(frames):
        seg = mono[i * hop:i * hop + nfft] * win
        S[:, i] = np.abs(np.fft.rfft(seg)) + 1e-12
    db = 20 * np.log10(S / S.max())
    freqs = np.fft.rfftfreq(nfft, 1 / sr)
    ax[1].pcolormesh(np.arange(frames) * hop / sr, freqs, db,
                     vmin=-90, vmax=0, cmap="magma", shading="auto")
    ax[1].set_yscale("symlog", linthresh=100)
    ax[1].set_ylim(20, sr / 2)
    ax[1].set_ylabel("Hz")
    ax[1].set_xlabel("secondi")
    fig.tight_layout()
    fig.savefig(dst, dpi=90)
    print(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
