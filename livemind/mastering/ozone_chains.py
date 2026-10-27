"""Catene Ozone 11 per genere + calcoli di tempo per effetti.

Sono PUNTI DI PARTENZA ragionati (vedi docs/knowledge/mastering/ozone11.md,
sezione 4), da validare con le misure (`livemind.audio.reference`) contro i
reference dell'utente. I nomi dei moduli e dei parametri sono quelli del
manuale Ozone 11, cosi' si possono cercare per nome via LOM
(`set_param_by_name`) quando Ozone e' caricato in Live.
"""
from __future__ import annotations

import copy

GENRES = ("hardtek", "tekno_tribe", "acid", "hardflor")
DESTINATIONS = ("club", "streaming")

# Range di loudness del DROP (short-term LUFS) per la destinazione club.
DROP_LUFS = {
    "hardtek": (-6.5, -5.0),
    "tekno_tribe": (-7.5, -6.0),
    "acid": (-8.0, -6.5),
    "hardflor": (-7.0, -5.5),
}

_IMAGER_CLUB = {
    "module": "Imager",
    "bands": [
        {"range_hz": (20, 120), "width": -100},   # mono sotto 120 Hz
        {"range_hz": (120, 2500), "width": 0},
        {"range_hz": (2500, 20000), "width": 8},
    ],
    "stereoize": False,
}

_BASE = {
    "hardtek": [
        {"module": "Equalizer 1", "filter_mode": "Analog", "channel_mode": "Mid/Side",
         "mid": [{"shape": "Highpass Flat", "freq_hz": 25, "slope_db_oct": 12}],
         "side": [{"shape": "Highpass Flat", "freq_hz": 150, "slope_db_oct": 12},
                  {"shape": "Baxandall Treble", "freq_hz": 10000, "gain_db": 0.8}]},
        {"module": "Dynamic EQ", "filter_mode": "Analog",
         "nodes": [{"shape": "Proportional Q", "freq_hz": 3200, "gain_db": -3.0,
                    "direction": "down", "target_gr_db": 1.5},
                   {"shape": "Proportional Q", "freq_hz": 280, "gain_db": -2.0,
                    "direction": "down", "target_gr_db": 1.0}]},
        {"module": "Low End Focus", "mode": "Punchy", "region_hz": (40, 180),
         "contrast": 15, "gain_db": 0.0},
        {"module": "Dynamics", "detection": "Env", "detection_filter": "Highpass 100 Hz",
         "bands": [{"range_hz": (20, 20000), "ratio": 1.5, "attack_ms": 30,
                    "release_ms": 120, "target_gr_db": 1.0, "parallel": 0}],
         "auto_gain": True, "adaptive_release": True},
        _IMAGER_CLUB,
        {"module": "Maximizer", "irc": "IRC 3", "style": "Crisp", "character": 3.0,
         "soft_clip": {"mode": "Moderate", "amount_pct": 40},
         "transient_emphasis": 15, "upward_compress_db": 0,
         "stereo_independence_pct": 0, "true_peak": True, "output_db": -1.0,
         "target_gr_db": (2, 4)},
    ],
    "tekno_tribe": [
        {"module": "Equalizer 1", "filter_mode": "Analog", "channel_mode": "Mid/Side",
         "mid": [{"shape": "Highpass Flat", "freq_hz": 25, "slope_db_oct": 12}],
         "side": [{"shape": "Highpass Flat", "freq_hz": 130, "slope_db_oct": 12}]},
        {"module": "Vintage Compressor", "mode": "Sharp", "ratio": 1.5,
         "attack_ms": 20, "release_ms": 150, "target_gr_db": 1.0, "auto_gain": True},
        {"module": "Impact", "bands": [
            {"range_hz": (20, 150), "impact": 10},
            {"range_hz": (150, 2000), "impact": 20},     # tom/bongo tribali
            {"range_hz": (2000, 20000), "impact": -5}],  # hat piu' morbidi
         "sync": True, "envelope": "1/16", "auto_gain": True},
        _IMAGER_CLUB,
        {"module": "Maximizer", "irc": "IRC 4", "style": "Transient", "character": 4.0,
         "soft_clip": {"mode": "Light", "amount_pct": 30},
         "transient_emphasis": 20, "upward_compress_db": 0,
         "stereo_independence_pct": 0, "true_peak": True, "output_db": -1.0,
         "target_gr_db": (2, 3)},
    ],
    "acid": [
        {"module": "Equalizer 1", "filter_mode": "Analog", "channel_mode": "Mid/Side",
         "mid": [{"shape": "Highpass Flat", "freq_hz": 25, "slope_db_oct": 12}],
         "side": [{"shape": "Highpass Flat", "freq_hz": 140, "slope_db_oct": 12}]},
        {"module": "Stabilizer", "mode": "Cut", "sensitivity": 50, "speed": 60,
         "amount": 60, "low_pct": 0, "mid_pct": 100, "high_pct": 60,
         "note": "doma le risonanze mobili del 303 senza toccare kick/sub"},
        {"module": "Spectral Shaper", "channel_mode": "Transient/Sustain",
         "process": "Sustain", "mode": "Low", "region_hz": (1000, 5000), "amount": 30},
        {"module": "Dynamics", "detection": "Env", "detection_filter": "Tilt",
         "bands": [{"range_hz": (20, 20000), "ratio": 1.5, "attack_ms": 25,
                    "release_ms": 150, "target_gr_db": 1.0, "parallel": 0}],
         "auto_gain": True, "adaptive_release": True},
        _IMAGER_CLUB,
        {"module": "Exciter", "oversampling": True, "bands": [
            {"range_hz": (20, 300), "mode": "off"},
            {"range_hz": (300, 3000), "mode": "Tube", "amount": 15, "mix_pct": 25},
            {"range_hz": (3000, 20000), "mode": "Tape", "amount": 10, "mix_pct": 20}]},
        {"module": "Maximizer", "irc": "IRC 4", "style": "Modern", "character": 4.0,
         "soft_clip": {"mode": "Light", "amount_pct": 25},
         "transient_emphasis": 10, "upward_compress_db": 1.5,
         "stereo_independence_pct": 0, "true_peak": True, "output_db": -1.0,
         "target_gr_db": (2, 3)},
    ],
    "hardflor": [
        {"module": "Equalizer 1", "filter_mode": "Analog", "channel_mode": "Mid/Side",
         "mid": [{"shape": "Highpass Flat", "freq_hz": 25, "slope_db_oct": 12}],
         "side": [{"shape": "Highpass Flat", "freq_hz": 140, "slope_db_oct": 12}]},
        {"module": "Low End Focus", "mode": "Punchy", "region_hz": (40, 200),
         "contrast": 20, "gain_db": 0.0},
        {"module": "Vintage EQ", "low_freq_hz": 60, "low_boost_db": 1.5,
         "low_cut_db": 1.0, "high_boost_freq_hz": 12000, "high_boost_db": 1.0},
        _IMAGER_CLUB,
        {"module": "Vintage Limiter", "mode": "Analog", "character": 5.0,
         "target_gr_db": (0.5, 1.5), "note": "glue grasso prima del Maximizer"},
        {"module": "Maximizer", "irc": "IRC 3", "style": "Balanced", "character": 3.0,
         "soft_clip": {"mode": "Moderate", "amount_pct": 30},
         "transient_emphasis": 15, "upward_compress_db": 0,
         "stereo_independence_pct": 0, "true_peak": True, "output_db": -1.0,
         "target_gr_db": (2, 4)},
    ],
}


def chain_for(genre: str, destination: str = "club") -> dict:
    """Catena Ozone 11 per genere e destinazione ('club' | 'streaming')."""
    g = genre.lower().replace("-", "_").replace(" ", "_")
    if g not in _BASE:
        raise ValueError(f"genere sconosciuto: {genre!r} (disponibili: {', '.join(GENRES)})")
    if destination not in DESTINATIONS:
        raise ValueError(f"destinazione sconosciuta: {destination!r}")
    modules = copy.deepcopy(_BASE[g])
    lufs = DROP_LUFS[g]
    if destination == "streaming":
        # stessa catena, meno limiting: la piattaforma normalizza comunque
        for m in modules:
            if m["module"] == "Maximizer":
                m["soft_clip"]["amount_pct"] = round(m["soft_clip"]["amount_pct"] / 2)
                m["target_gr_db"] = (1, 2)
                m["output_db"] = -1.0
        lufs = (-10.0, -8.0)
    return {"genre": g, "destination": destination,
            "drop_short_term_lufs": lufs, "true_peak_max_dbtp": -1.0,
            "modules": modules}


def describe(chain: dict) -> str:
    """Riassunto testuale leggibile di una catena."""
    lo, hi = chain["drop_short_term_lufs"]
    lines = [f"Ozone 11 — {chain['genre']} ({chain['destination']}): drop {lo}..{hi} LUFS "
             f"short-term, TP <= {chain['true_peak_max_dbtp']} dBTP"]
    for i, m in enumerate(chain["modules"], 1):
        extra = {k: v for k, v in m.items() if k != "module"}
        lines.append(f"{i}. {m['module']}: {extra}")
    return "\n".join(lines)


_DIV = {"1/1": 4.0, "1/2": 2.0, "1/4": 1.0, "1/8": 0.5, "1/16": 0.25,
        "1/32": 0.125, "1/64": 0.0625}


def delay_ms(bpm: float, division: str = "1/4") -> float:
    """Tempo in ms di una divisione ('1/8', '1/8d' puntata, '1/8t' terzina)."""
    if bpm <= 0:
        raise ValueError("bpm deve essere > 0")
    d = division.strip().lower()
    mult = 1.0
    if d.endswith("d"):
        mult, d = 1.5, d[:-1]
    elif d.endswith("t"):
        mult, d = 2.0 / 3.0, d[:-1]
    if d not in _DIV:
        raise ValueError(f"divisione sconosciuta: {division!r}")
    return round(60000.0 / bpm * _DIV[d] * mult, 1)


def comp_release_hint_ms(bpm: float) -> tuple[float, float]:
    """Range di release che 'respira' tra un kick e l'altro (30-70% di un 1/4)."""
    q = 60000.0 / bpm
    return round(q * 0.3), round(q * 0.7)
