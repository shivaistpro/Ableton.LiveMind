import numpy as np
from livemind.audio.analyzer import true_peak_dbtp, spectral_balance


def test_true_peak_full_scale_sine():
    sr = 48000
    t = np.arange(sr) / sr
    x = np.sin(2 * np.pi * 997 * t).astype(np.float64)
    tp = true_peak_dbtp(x, sr)
    assert -0.5 < tp < 0.5  # ~0 dBTP


def test_true_peak_minus6():
    sr = 48000
    t = np.arange(sr) / sr
    x = 0.5 * np.sin(2 * np.pi * 440 * t)
    tp = true_peak_dbtp(x, sr)
    assert -6.6 < tp < -5.4


def test_spectral_balance_bass_heavy():
    sr = 48000
    t = np.arange(sr) / sr
    x = np.sin(2 * np.pi * 80 * t) + 0.05 * np.sin(2 * np.pi * 4000 * t)
    b = spectral_balance(x, sr)
    assert b["bass"] > b["highmid"] + 10  # basso dominante


def test_spectral_balance_keys():
    sr = 48000
    x = np.random.randn(sr // 2) * 0.1
    b = spectral_balance(x, sr)
    assert set(b) == {"sub", "bass", "lowmid", "mid", "highmid", "high"}
