import numpy as np
import pytest

pytest.importorskip("pedalboard")
sf = pytest.importorskip("soundfile")

from livemind.audio.dsp import process, render
from livemind.brain.tools import dispatch

SR = 48000


def _sine(f, sec=0.5, amp=0.5):
    t = np.arange(int(SR * sec)) / SR
    return (amp * np.sin(2 * np.pi * f * t)).astype(np.float32)[None, :]


def _alias_energy(y, f0):
    """Energia fuori dalle armoniche di f0 (= aliasing), in dB relativi."""
    x = y[0, SR // 10:]
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / SR)
    harm = np.zeros_like(spec, dtype=bool)
    for k in range(1, int(SR / 2 / f0) + 1):
        harm |= np.abs(freqs - k * f0) < 30
    return 10 * np.log10(spec[~harm].sum() / spec[harm].sum())


def test_null_empty_chain(tmp_path):
    src, dst = tmp_path / "a.wav", tmp_path / "b.wav"
    sf.write(src, _sine(220).T, SR, subtype="PCM_24")
    render(str(src), str(dst), [])
    a, _ = sf.read(src)
    b, _ = sf.read(dst)
    assert np.max(np.abs(a - b)) < 1e-6


def test_distortion_adds_odd_harmonics():
    y = process(_sine(1000), SR, [{"type": "distortion", "drive_db": 24}])
    spec = np.abs(np.fft.rfft(y[0]))
    bin_hz = SR / y.shape[1]
    h1, h3 = spec[int(1000 / bin_hz)], spec[int(3000 / bin_hz)]
    assert h3 / h1 > 0.05


def test_oversampling_reduces_aliasing():
    x = _sine(7919, amp=0.9)
    chain = [{"type": "clipping", "threshold_db": -12}]
    raw = _alias_energy(process(x, SR, chain, oversample=1), 7919)
    os4 = _alias_energy(process(x, SR, chain, oversample=4), 7919)
    assert os4 < raw - 10


def test_tail_and_normalize(tmp_path):
    src, dst = tmp_path / "a.wav", tmp_path / "b.wav"
    sf.write(src, _sine(110, sec=0.2).T, SR)
    r = render(str(src), str(dst), [{"type": "reverb", "room_size": 0.8}],
               tail_s=1.0, normalize_dbfs=-1.0)
    assert r["seconds"] == pytest.approx(1.2, abs=0.01)
    assert r["peak_dbfs"] == pytest.approx(-1.0, abs=0.05)


def test_ladder_mode_string_and_unknown_effect():
    process(_sine(200), SR, [{"type": "ladder", "mode": "lpf24", "cutoff_hz": 800, "resonance": 0.7}])
    with pytest.raises(ValueError):
        process(_sine(200), SR, [{"type": "flanger3000"}])


def test_dispatch_dsp_render(tmp_path):
    src, dst = tmp_path / "a.wav", tmp_path / "b.wav"
    sf.write(src, _sine(60).T, SR)
    out = dispatch("dsp_render", {"src": str(src), "dst": str(dst),
                                  "chain": [{"type": "compressor", "threshold_db": -20, "ratio": 4}]}, live=None)
    assert "peak_dbfs" in out and dst.exists()
