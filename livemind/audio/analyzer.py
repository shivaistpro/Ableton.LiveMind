"""Analisi del master: LUFS (BS.1770 via pyloudnorm), true peak, bilanciamento spettrale.

Le funzioni DSP sono pure (numpy) e testabili; la cattura audio è separata.
Per misurare il master di Live su Windows: abilitare loopback WASAPI
(sounddevice, device "Stereo Mix" o loopback del driver).
"""
from __future__ import annotations
import numpy as np

try:
    import pyloudnorm as pyln
    _HAS_PYLN = True
except ImportError:  # pragma: no cover
    _HAS_PYLN = False

try:
    import sounddevice as sd
    _HAS_SD = True
except ImportError:  # pragma: no cover
    _HAS_SD = False

BANDS = {"sub": (20, 60), "bass": (60, 120), "lowmid": (120, 500),
         "mid": (500, 2000), "highmid": (2000, 6000), "high": (6000, 16000)}


def true_peak_dbtp(x: np.ndarray, sr: int, oversample: int = 4) -> float:
    """True peak con oversampling FFT (approssimazione ITU-R BS.1770-4)."""
    if x.ndim == 1:
        x = x[:, None]
    peaks = []
    for ch in range(x.shape[1]):
        sig = x[:, ch]
        n = len(sig)
        spec = np.fft.rfft(sig)
        up = np.fft.irfft(spec, n * oversample) * oversample
        peaks.append(np.max(np.abs(up)))
    p = max(peaks)
    return float(20 * np.log10(p)) if p > 0 else -np.inf


def spectral_balance(x: np.ndarray, sr: int) -> dict[str, float]:
    """Energia RMS in dB per banda (mono somma)."""
    if x.ndim > 1:
        x = x.mean(axis=1)
    n = len(x)
    if n < 256:
        return {k: float("-inf") for k in BANDS}
    win = np.hanning(n)
    spec = np.abs(np.fft.rfft(x * win)) / (n / 2)
    freqs = np.fft.rfftfreq(n, 1 / sr)
    out = {}
    for name, (lo, hi) in BANDS.items():
        m = (freqs >= lo) & (freqs < hi)
        e = np.sqrt(np.mean(spec[m] ** 2)) if m.any() else 0.0
        out[name] = float(20 * np.log10(e)) if e > 0 else float("-inf")
    return out


def integrated_lufs(x: np.ndarray, sr: int) -> float:
    if not _HAS_PYLN:
        raise RuntimeError("pip install pyloudnorm")
    meter = pyln.Meter(sr)
    return float(meter.integrated_loudness(x))


class MasterAnalyzer:
    """Cattura loopback + report. `device` = indice/nome device sounddevice."""

    def __init__(self, samplerate: int = 48000, device=None):
        if not _HAS_SD:
            raise RuntimeError("pip install sounddevice")
        self.sr = samplerate
        self.device = device

    def capture(self, seconds: float) -> np.ndarray:
        rec = sd.rec(int(seconds * self.sr), samplerate=self.sr,
                     channels=2, device=self.device, dtype="float32")
        sd.wait()
        return rec

    def measure(self, seconds: float = 8.0) -> dict:
        x = self.capture(seconds)
        report = {
            "lufs_integrated": round(integrated_lufs(x, self.sr), 2),
            "true_peak_dbtp": round(true_peak_dbtp(x, self.sr), 2),
            "spectral_balance_db": {k: round(v, 1)
                                    for k, v in spectral_balance(x, self.sr).items()},
        }
        return report
