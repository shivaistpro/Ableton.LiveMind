"""Catene di effetti scritte in Python (pedalboard), renderizzate offline su un
file audio: distorsione, compressione, EQ, filtri, riverbero, delay...

Serve a lavorare un sample/stem fuori da Live (kick distorti, rumble, layer
sporchi) e reimportarlo con il tool 'sample' (create_audio_clip).

Uso:
    python -m livemind.audio.dsp in.wav out.wav '[{"type":"distortion","drive_db":18},
                                                 {"type":"lowpass","cutoff_frequency_hz":9000}]'

Ogni stadio = {"type": <nome>, ...parametri pedalboard con lo stesso nome}.
Gli stadi non lineari (distortion, clipping, ladder, bitcrush) girano in
oversampling (default 4x) contro l'aliasing.
"""
from __future__ import annotations
import json
import sys

import numpy as np

# type -> nome classe pedalboard
EFFECTS = {
    "gain": "Gain",
    "distortion": "Distortion",        # drive_db (tanh)
    "clipping": "Clipping",            # threshold_db (hard clip)
    "bitcrush": "Bitcrush",            # bit_depth
    "ladder": "LadderFilter",          # mode, cutoff_hz, resonance, drive
    "compressor": "Compressor",        # threshold_db, ratio, attack_ms, release_ms
    "limiter": "Limiter",              # threshold_db, release_ms
    "highpass": "HighpassFilter",      # cutoff_frequency_hz
    "lowpass": "LowpassFilter",
    "peak": "PeakFilter",              # cutoff_frequency_hz, gain_db, q
    "lowshelf": "LowShelfFilter",
    "highshelf": "HighShelfFilter",
    "reverb": "Reverb",                # room_size, damping, wet_level, dry_level, width
    "delay": "Delay",                  # delay_seconds, feedback, mix
    "chorus": "Chorus",
    "phaser": "Phaser",
}
NONLINEAR = {"distortion", "clipping", "ladder", "bitcrush"}


def _make(stage: dict):
    import pedalboard
    stage = dict(stage)
    kind = stage.pop("type", None)
    if kind not in EFFECTS:
        raise ValueError(f"effetto sconosciuto: {kind!r} (validi: {sorted(EFFECTS)})")
    cls = getattr(pedalboard, EFFECTS[kind])
    if kind == "ladder" and isinstance(stage.get("mode"), str):
        stage["mode"] = getattr(pedalboard.LadderFilter.Mode, stage["mode"].upper())
    return kind, cls(**stage)


def process(x: np.ndarray, sr: int, chain: list[dict], oversample: int = 4) -> np.ndarray:
    """x: (canali, campioni) float32. Ritorna lo stesso shape."""
    from scipy.signal import resample_poly
    y = np.asarray(x, dtype=np.float32)
    for stage in chain:
        kind, fx = _make(stage)
        if kind in NONLINEAR and oversample > 1:
            up = resample_poly(y, oversample, 1, axis=1).astype(np.float32)
            up = fx(up, sr * oversample)
            y = resample_poly(up, 1, oversample, axis=1)[:, : y.shape[1]].astype(np.float32)
        else:
            y = fx(y, sr)
    return y


def _db(v: float) -> float:
    return float(20 * np.log10(max(v, 1e-12)))


def render(src: str, dst: str, chain: list[dict], oversample: int = 4,
           tail_s: float = 0.0, normalize_dbfs: float | None = None) -> dict:
    """Legge src, applica chain, scrive dst (WAV 24 bit). tail_s aggiunge
    silenzio in coda per non tagliare le code di reverb/delay.
    normalize_dbfs normalizza il PICCO campione (non true peak)."""
    import soundfile as sf
    data, sr = sf.read(src, dtype="float32", always_2d=True)
    x = data.T
    if tail_s > 0:
        x = np.pad(x, ((0, 0), (0, int(tail_s * sr))))
    y = process(x, sr, chain, oversample)
    peak = float(np.max(np.abs(y))) if y.size else 0.0
    if normalize_dbfs is not None and peak > 0:
        y = y * (10 ** (normalize_dbfs / 20) / peak)
        peak = float(np.max(np.abs(y)))
    sf.write(dst, y.T, sr, subtype="PCM_24")
    rms = float(np.sqrt(np.mean(y ** 2))) if y.size else 0.0
    return {"dst": dst, "sr": sr, "channels": y.shape[0], "seconds": round(y.shape[1] / sr, 3),
            "peak_dbfs": round(_db(peak), 2), "rms_dbfs": round(_db(rms), 2),
            "clipped": peak > 1.0}


def dispatch(args: dict) -> str:
    chain = args.get("chain") or []
    if isinstance(chain, str):
        chain = json.loads(chain)
    return str(render(args["src"], args["dst"], chain, int(args.get("oversample", 4)),
                      float(args.get("tail_s", 0.0)), args.get("normalize_dbfs")))


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    print(render(sys.argv[1], sys.argv[2], json.loads(sys.argv[3])))
