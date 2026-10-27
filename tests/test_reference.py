"""Test di livemind/audio/reference.py .

Audio sintetico con metriche note; i WAV si scrivono con la stdlib (niente soundfile).
"""
from __future__ import annotations

import struct
import wave
from pathlib import Path

import numpy as np
import pytest

from livemind.audio import reference as ref
from livemind.audio.reference import (
    BANDS, TrackMetrics, average, compare, extract_metrics, recommendations,
)

SR = 44100


def _write_wav16(path: Path, x: np.ndarray, sr: int = SR) -> None:
    x = np.atleast_2d(x.T).T if x.ndim == 1 else x
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(x.shape[1])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def _write_wav_raw(path: Path, payload: bytes, tag: int, ch: int, sr: int, bits: int) -> None:
    ba = ch * bits // 8
    fmt = struct.pack("<HHIIHH", tag, ch, sr, sr * ba, ba, bits)
    body = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", len(payload)) + payload
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)


def _make_track(path: Path, duration=8.0, gain_db=-6.0, sub_boost=1.0, width=0.0, seed=0) -> None:
    """Kick 60 Hz ogni 0.5 s + basso 200 Hz + pad 4 kHz + rumore; width 0 = mono."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(SR * duration)) / SR
    kick = np.zeros_like(t)
    for k in range(int(duration / 0.5)):
        s = int(k * 0.5 * SR)
        e = min(s + int(0.15 * SR), len(t))
        kt = np.arange(e - s) / SR
        kick[s:e] += 0.6 * sub_boost * np.sin(2 * np.pi * 60 * kt) * np.exp(-12 * kt)
    bass = 0.2 * np.sin(2 * np.pi * 200 * t)
    pad = 0.15 * np.sin(2 * np.pi * 4000 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.5 * t))
    mono = kick + bass + pad + 0.05 * rng.standard_normal(len(t))
    mono *= 10 ** (gain_db / 20) / np.max(np.abs(mono))
    dec = rng.standard_normal(len(t)) * 0.02
    _write_wav16(path, np.column_stack([mono + width * dec, mono - width * dec]))


@pytest.fixture
def reference_set(tmp_path):
    out = []
    for i in range(3):
        p = tmp_path / f"ref_{i}.wav"
        _make_track(p, gain_db=-7.0, sub_boost=1.4, width=0.6, seed=100 + i)
        out.append(p)
    return out


@pytest.fixture
def quiet_mix(tmp_path):
    p = tmp_path / "quiet_mix.wav"
    _make_track(p, gain_db=-18.0, sub_boost=0.6, width=0.0, seed=0)
    return p


@pytest.fixture
def matching_mix(tmp_path):
    p = tmp_path / "matching_mix.wav"
    _make_track(p, gain_db=-7.0, sub_boost=1.4, width=0.6, seed=999)
    return p


ZERO = {"lufs": 0.0, "lra": 0.0, "true_peak": 0.0, "crest_factor": 0.0, "stereo_width": 0.0}


# --- lettura WAV --------------------------------------------------------------

def test_read_wav_pcm24_and_float32(tmp_path):
    x = np.array([0.0, 0.5, -0.5, 0.25], dtype=np.float64)
    v = np.round(x * (1 << 23)).astype(np.int32)
    b24 = b"".join(int(s & 0xFFFFFF).to_bytes(3, "little") for s in v)
    _write_wav_raw(tmp_path / "a.wav", b24, 1, 1, 48000, 24)
    y, sr = ref._read_wav(tmp_path / "a.wav")
    assert sr == 48000 and y.shape == (4, 1)
    assert np.allclose(y[:, 0], x, atol=1e-6)

    stereo = np.array([[0.1, -0.2], [0.3, -0.4]], dtype="<f4")
    _write_wav_raw(tmp_path / "f.wav", stereo.tobytes(), 3, 2, 44100, 32)
    y, sr = ref._read_wav(tmp_path / "f.wav")
    assert y.shape == (2, 2) and np.allclose(y, stereo)


# --- DSP ----------------------------------------------------------------------

def test_short_term_matches_pyloudnorm_on_steady_sine():
    t = np.arange(SR * 6) / SR
    x = 0.3 * np.sin(2 * np.pi * 1000 * t)
    st = ref.short_term_loudness(x, SR)
    assert abs(float(np.median(st)) - ref.integrated_lufs(x[:, None], SR)) < 0.2


def test_lra_steady_vs_two_levels():
    t = np.arange(SR * 20) / SR
    steady = 0.3 * np.sin(2 * np.pi * 1000 * t)
    assert ref.loudness_range(steady, SR) < 0.5
    two = steady.copy()
    two[len(two) // 2:] *= 10 ** (-10 / 20)   # seconda meta' -10 dB
    assert 8.0 < ref.loudness_range(two, SR) < 11.0


def test_true_peak_blocked_equals_single_pass():
    rng = np.random.default_rng(1)
    x = rng.standard_normal((50000, 2)) * 0.2
    assert abs(ref.true_peak_dbtp(x, block=4096) - ref.true_peak_dbtp(x, block=1 << 20)) < 1e-6


def test_true_peak_catches_intersample_over():
    # sinusoide a fs/4 con fase 45 deg: i campioni stanno a 0.707, il picco reale a 1.0
    n = np.arange(4000)
    x = np.sin(np.pi / 2 * n + np.pi / 4) / np.sqrt(0.5) * 0.9   # campioni a 0.9, vero picco ~1.27
    tp = ref.true_peak_dbtp(x)
    assert tp > 1.5          # sample peak sarebbe -0.9 dBFS


def test_band_energy_fractions():
    t = np.arange(SR * 2) / SR
    b = ref.band_energy(np.sin(2 * np.pi * 100 * t), SR)
    assert b["bass"] > 0.95 and abs(sum(b.values()) - 1.0) < 0.01


# --- metriche e confronto (casi di riferimento) -----------------------------------

def test_extract_metrics_returns_all_fields(quiet_mix):
    m = extract_metrics(quiet_mix)
    assert isinstance(m, TrackMetrics)
    assert m.lufs < 0 and m.true_peak_dbtp <= 1.0 and m.crest_factor_db > 0
    assert 0.0 <= m.stereo_width <= 2.0
    assert set(m.bands) == set(BANDS)
    assert sum(m.bands.values()) <= 1.01


def test_quiet_mix_triggers_lufs_recommendation(quiet_mix, reference_set):
    r = compare(quiet_mix, reference_set, use_cache=False)
    assert r.deltas["lufs"] < -3.0
    assert any("alza gain" in x.lower() for x in r.recommendations)


def test_mono_mix_triggers_stereo_recommendation(quiet_mix, reference_set):
    r = compare(quiet_mix, reference_set, use_cache=False)
    assert r.deltas["stereo_width"] < -0.05
    assert any("stereo" in x.lower() for x in r.recommendations)


def test_matching_mix_is_within_tolerance(matching_mix, reference_set):
    r = compare(matching_mix, reference_set, use_cache=False)
    assert abs(r.deltas["lufs"]) < 1.5
    assert abs(r.deltas["stereo_width"]) < 0.15


def test_average():
    flat = {b: 1 / len(BANDS) for b in BANDS}
    m1 = TrackMetrics("a", -10.0, 8.0, -1.0, 12.0, 0.5, dict(flat))
    m2 = TrackMetrics("b", -8.0, 10.0, -0.5, 14.0, 0.7, dict(flat))
    avg = average([m1, m2])
    assert (avg.lufs, avg.lra, avg.stereo_width) == (-9.0, 9.0, 0.6)


def test_recommendations_clean_when_within_tolerance():
    d = {"lufs": 0.1, "lra": 0.5, "true_peak": 0.1, "crest_factor": 0.5, "stereo_width": 0.02}
    recs = recommendations(d, {b: 0.005 for b in BANDS})
    assert len(recs) == 1 and "pronto per il master" in recs[0].lower()


def test_absolute_true_peak_over_zero_is_flagged_even_if_refs_are_hot():
    recs = recommendations(dict(ZERO), {b: 0.0 for b in BANDS}, mix_true_peak=2.0)
    assert any("inter-sample" in r for r in recs)


def test_ratio_aware_sub_bass_rebalance():
    """Caso reale Solid Snake: sub +13.6%, bass -12.4% -> aggiungi bass, NON tagliare sub."""
    bd = {b: 0.0 for b in BANDS}
    bd["sub"], bd["bass"] = 0.136, -0.124
    recs = recommendations(dict(ZERO), bd)
    text = " ".join(recs).lower()
    assert "sbilanciato" in text
    assert "aggiungi energia in bass" in text
    assert "non tagliare sub" in text
    assert not any("taglia con eq" in r.lower() and "sub" in r.lower() for r in recs)


def test_ratio_aware_single_band_stays_standard():
    bd = {b: 0.0 for b in BANDS}
    bd["air"] = -0.05
    text = " ".join(recommendations(dict(ZERO), bd)).lower()
    assert "air" in text and "manca energia" in text and "sbilanciato" not in text


def test_ratio_aware_non_adjacent_bands_dont_pair():
    bd = {b: 0.0 for b in BANDS}
    bd["sub"], bd["high"] = 0.10, -0.10
    recs = recommendations(dict(ZERO), bd)
    assert "sbilanciato" not in " ".join(recs).lower()
    assert sum(1 for r in recs if "sub" in r.lower() or "high" in r.lower()) >= 2


def test_ratio_aware_chain_does_not_reuse_a_band():
    """sub+ bass- low_mid+ : bass va accoppiato una volta sola."""
    bd = {b: 0.0 for b in BANDS}
    bd["sub"], bd["bass"], bd["low_mid"] = 0.10, -0.10, 0.09
    recs = recommendations(dict(ZERO), bd)
    assert sum("sbilanciato" in r for r in recs) == 1
    assert any(r.startswith("Banda low_mid") for r in recs)


# --- reference per genere + cache -----------------------------------------------

def test_genre_refs_and_cache(tmp_path, monkeypatch):
    g = tmp_path / "hardtek"
    g.mkdir()
    for i in range(2):
        _make_track(g / f"r{i}.wav", duration=4.0, seed=i)
    (g / "note.txt").write_text("x")
    paths = ref.genre_refs("hardtek", tmp_path)
    assert [p.name for p in paths] == ["r0.wav", "r1.wav"]
    assert ref.available_genres(tmp_path) == ["hardtek"]

    first = ref.cached_metrics(paths)
    assert (g / ref.CACHE_NAME).exists()
    monkeypatch.setattr(ref, "extract_metrics", lambda p: pytest.fail("cache ignorata"))
    second = ref.cached_metrics(paths)
    assert [m.lufs for m in first] == [m.lufs for m in second]


def test_cli_writes_json_report(tmp_path, monkeypatch, capsys, quiet_mix, reference_set):
    monkeypatch.setattr(ref, "OUT_DIR", tmp_path / "out")
    rc = ref.main([str(quiet_mix), "--refs", *map(str, reference_set), "--no-cache"])
    assert rc == 0
    assert "Raccomandazioni" in capsys.readouterr().out
    assert len(list((tmp_path / "out").glob("reference_quiet_mix_*.json"))) == 1


def test_cli_unknown_genre_fails(tmp_path, monkeypatch, quiet_mix):
    monkeypatch.setattr(ref, "REFS_DIR", tmp_path)
    assert ref.main([str(quiet_mix), "--genre", "nope"]) == 1
