"""Reference matching: confronta un mix con brani di riferimento dello stesso genere.

Modulo autonomo di LIVEMIND:
niente typer/rich/soundfile obbligatori, solo numpy + pyloudnorm (+ scipy, che
pyloudnorm porta gia' con se').

Metriche: LUFS integrato, LRA (EBU Tech 3342), true peak (4x), crest factor,
stereo width (Side/Mid), bilanciamento spettrale su 7 bande come FRAZIONE di
energia totale (non dB assoluti: cosi' il confronto non dipende dal volume).

Il pezzo di valore e' la logica **ratio-aware** sulle bande: se due bande
adiacenti hanno delta opposti che si compensano (es. sub +13%, bass -12%),
il problema non e' "troppo sub" ma "manca corpo nel bass". Tagliare il sub
toglierebbe la fondazione del kick; il fix giusto e' aggiungere armoniche
nella banda mancante (saturazione / shelf).

Uso (dalla root di LIVEMIND):
    python -m livemind.audio.reference mix.wav --genre hardtek
    python -m livemind.audio.reference mix.wav --refs a.wav b.wav
    python -m livemind.audio.reference --loopback 20 --genre hardtek   # uscita di Live

I reference stanno in references/<genere>/*.wav (audio fuori da Git).
Il report JSON va in bridge/audio/ (leggibile dall agente via bridge).

STATO: sperimentale. Limiti noti e cose da migliorare in CLAUDE.md,
sezione "Confronto con i reference".
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
REFS_DIR = Path(os.environ.get("LIVEMIND_REFS", ROOT / "references"))
OUT_DIR = ROOT / "bridge" / "audio"
CACHE_NAME = ".metrics_cache.json"

# --- Bande spettrali (Hz) -------------------------------------------------
BANDS: dict[str, tuple[float, float]] = {
    "sub": (20.0, 60.0),
    "bass": (60.0, 250.0),
    "low_mid": (250.0, 500.0),
    "mid": (500.0, 2000.0),
    "high_mid": (2000.0, 6000.0),
    "high": (6000.0, 12000.0),
    "air": (12000.0, 20000.0),
}

# --- Tolleranze "match accettabile" ---------------------------------------
TOLERANCES: dict[str, float] = {
    "lufs": 0.5,          # LU
    "lra": 1.5,           # LU
    "true_peak": 0.5,     # dB
    "crest_factor": 2.0,  # dB
    "stereo_width": 0.10,  # rapporto S/M
    "band_ratio": 0.02,   # 2 punti percentuali di energia
}

# Oltre questo il limiter lascia passare inter-sample over: vale a prescindere
# dai reference (molti master club stanno a 0 dBTP, ma sopra si distorce nei DAC).
TP_ABS_LIMIT = 0.0


@dataclass
class TrackMetrics:
    file: str
    lufs: float
    lra: float
    true_peak_dbtp: float
    crest_factor_db: float
    stereo_width: float
    bands: dict[str, float] = field(default_factory=dict)


@dataclass
class ComparisonReport:
    mix: TrackMetrics
    reference_files: list[str]
    reference_avg: TrackMetrics
    deltas: dict[str, float]
    band_deltas: dict[str, float]
    recommendations: list[str] = field(default_factory=list)


# --- Lettura audio ---------------------------------------------------------

def _read_wav(path: Path) -> tuple[np.ndarray, int]:
    """Parser RIFF/WAVE minimale: PCM 8/16/24/32 bit, float 32/64, extensible."""
    data = path.read_bytes()
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError(f"{path.name}: non e' un WAV RIFF")
    pos, fmt, raw = 12, None, None
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4]
        size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        body = data[pos + 8:pos + 8 + size]
        if cid == b"fmt ":
            tag, ch, sr, _, _, bits = struct.unpack("<HHIIHH", body[:16])
            if tag == 0xFFFE and len(body) >= 26:
                tag = struct.unpack("<H", body[24:26])[0]
            fmt = (tag, ch, sr, bits)
        elif cid == b"data":
            raw = body
        pos += 8 + size + (size & 1)
    if fmt is None or raw is None:
        raise ValueError(f"{path.name}: chunk fmt/data mancante")
    tag, ch, sr, bits = fmt
    width = bits // 8
    raw = raw[: len(raw) - len(raw) % (width * ch)]
    if tag == 3:
        x = np.frombuffer(raw, dtype="<f4" if bits == 32 else "<f8").astype(np.float32)
    elif tag == 1:
        if bits == 8:
            x = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
        elif bits == 16:
            x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
        elif bits == 24:
            b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
            v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
            v = np.where(v >= 1 << 23, v - (1 << 24), v)
            x = v.astype(np.float32) / float(1 << 23)
        elif bits == 32:
            x = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
        else:
            raise ValueError(f"{path.name}: PCM {bits} bit non supportato")
    else:
        raise ValueError(f"{path.name}: formato WAV {tag} non supportato")
    return x.reshape(-1, ch), sr


def load_audio(path: Path) -> tuple[np.ndarray, int]:
    """Ritorna (frames x canali float32, sr). soundfile se c'e' (flac/aiff), altrimenti WAV."""
    path = Path(path)
    try:
        import soundfile as sf
        x, sr = sf.read(str(path), always_2d=True, dtype="float32")
        return x, sr
    except ImportError:
        return _read_wav(path)


# --- DSP -------------------------------------------------------------------

def _k_weight(x: np.ndarray, sr: int) -> np.ndarray:
    """K-weighting BS.1770 con gli stessi filtri del Meter di pyloudnorm,
    cosi' short-term e integrato sono coerenti tra loro."""
    import pyloudnorm as pyln
    y = x.astype(np.float64)
    for f in pyln.Meter(sr)._filters.values():
        y = f.apply_filter(y.T).T      # lfilter lavora sull'ultimo asse
    return y


def integrated_lufs(x: np.ndarray, sr: int) -> float:
    import pyloudnorm as pyln
    return float(pyln.Meter(sr).integrated_loudness(x))


def short_term_loudness(x: np.ndarray, sr: int, hop_s: float = 0.1) -> np.ndarray:
    """Loudness short-term (finestra 3 s) ogni hop_s secondi, in LUFS."""
    if x.ndim == 1:
        x = x[:, None]
    y = _k_weight(x, sr)
    win, hop = int(3.0 * sr), max(1, int(hop_s * sr))
    if len(y) < win:
        return np.array([])
    # somma cumulativa dei quadrati: media mobile in O(n)
    cs = np.vstack([np.zeros((1, y.shape[1])), np.cumsum(y ** 2, axis=0)])
    starts = np.arange(0, len(y) - win + 1, hop)
    ms = (cs[starts + win] - cs[starts]) / win          # (blocchi, canali)
    power = ms.sum(axis=1)                               # pesi canale L/R = 1.0
    with np.errstate(divide="ignore"):
        return -0.691 + 10 * np.log10(power)


def loudness_range(x: np.ndarray, sr: int) -> float:
    """LRA secondo EBU Tech 3342: gate assoluto -70, relativo -20 LU, p95 - p10."""
    st = short_term_loudness(x, sr)
    st = st[np.isfinite(st) & (st > -70.0)]
    if len(st) < 2:
        return 0.0
    rel_gate = 10 * np.log10(np.mean(10 ** (st / 10))) - 20.0
    st = st[st > rel_gate]
    if len(st) < 2:
        return 0.0
    return float(np.percentile(st, 95) - np.percentile(st, 10))


def true_peak_dbtp(x: np.ndarray, oversample: int = 4, block: int = 1 << 18) -> float:
    """True peak con resample polifase 4x, a blocchi (niente GB di RAM sui brani lunghi)."""
    from scipy.signal import resample_poly
    if x.ndim == 1:
        x = x[:, None]
    margin = 64
    peak = 0.0
    n = len(x)
    for ch in range(x.shape[1]):
        sig = x[:, ch].astype(np.float64)
        for s in range(0, n, block):
            lo, hi = max(0, s - margin), min(n, s + block + margin)
            up = resample_poly(sig[lo:hi], oversample, 1)
            a = (s - lo) * oversample
            b = a + (min(n, s + block) - s) * oversample
            peak = max(peak, float(np.max(np.abs(up[a:b]))))
    return float(20 * np.log10(peak)) if peak > 0 else float("-inf")


def crest_factor_db(x: np.ndarray) -> float:
    mono = x.mean(axis=1) if x.ndim == 2 else x
    peak = float(np.max(np.abs(mono)))
    rms = float(np.sqrt(np.mean(mono.astype(np.float64) ** 2)))
    return float(20 * np.log10((peak + 1e-12) / (rms + 1e-12)))


def stereo_width(x: np.ndarray) -> float:
    """RMS(Side)/RMS(Mid): 0 = mono, ~1 = molto largo, >1 = fuori fase."""
    if x.ndim != 2 or x.shape[1] < 2:
        return 0.0
    l, r = x[:, 0].astype(np.float64), x[:, 1].astype(np.float64)
    mid, side = (l + r) * 0.5, (l - r) * 0.5
    return float(np.sqrt(np.mean(side ** 2)) / (np.sqrt(np.mean(mid ** 2)) + 1e-12))


def band_energy(x: np.ndarray, sr: int, nfft: int = 8192) -> dict[str, float]:
    """Frazione di energia per banda (Welch, finestra Hann) sul mono-sum."""
    mono = (x.mean(axis=1) if x.ndim == 2 else x).astype(np.float64)
    if len(mono) < nfft:
        mono = np.pad(mono, (0, nfft - len(mono)))
    hop = nfft // 2
    win = np.hanning(nfft)
    freqs = np.fft.rfftfreq(nfft, 1 / sr)
    psd = np.zeros(len(freqs))
    starts = np.arange(0, len(mono) - nfft + 1, hop)
    for i in range(0, len(starts), 256):          # batch: RAM costante
        idx = starts[i:i + 256, None] + np.arange(nfft)
        psd += (np.abs(np.fft.rfft(mono[idx] * win, axis=1)) ** 2).sum(axis=0)
    total = float(psd.sum()) + 1e-12
    return {name: float(psd[(freqs >= lo) & (freqs < hi)].sum() / total)
            for name, (lo, hi) in BANDS.items()}


def metrics_from_array(x: np.ndarray, sr: int, name: str = "<array>") -> TrackMetrics:
    if x.ndim == 1:
        x = x[:, None]
    return TrackMetrics(
        file=name,
        lufs=round(integrated_lufs(x, sr), 2),
        lra=round(loudness_range(x, sr), 2),
        true_peak_dbtp=round(true_peak_dbtp(x), 2),
        crest_factor_db=round(crest_factor_db(x), 2),
        stereo_width=round(stereo_width(x), 3),
        bands={k: round(v, 4) for k, v in band_energy(x, sr).items()},
    )


def extract_metrics(path: Path) -> TrackMetrics:
    x, sr = load_audio(Path(path))
    return metrics_from_array(x, sr, str(path))


# --- Reference set ---------------------------------------------------------

def genre_refs(genre: str, refs_dir: Path | None = None) -> list[Path]:
    d = Path(refs_dir or REFS_DIR) / genre
    if not d.is_dir():
        return []
    exts = {".wav", ".flac", ".aif", ".aiff"}
    return sorted(p for p in d.iterdir() if p.suffix.lower() in exts)


def available_genres(refs_dir: Path | None = None) -> list[str]:
    d = Path(refs_dir or REFS_DIR)
    return sorted(p.name for p in d.iterdir() if p.is_dir() and genre_refs(p.name, d)) if d.is_dir() else []


def cached_metrics(paths: list[Path]) -> list[TrackMetrics]:
    """Misura i reference usando una cache per cartella (chiave: nome+size+mtime)."""
    out: list[TrackMetrics] = []
    by_dir: dict[Path, dict] = {}
    dirty: set[Path] = set()
    for p in map(Path, paths):
        cfile = p.parent / CACHE_NAME
        if p.parent not in by_dir:
            try:
                by_dir[p.parent] = json.loads(cfile.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                by_dir[p.parent] = {}
        st = p.stat()
        key = f"{p.name}|{st.st_size}|{int(st.st_mtime)}"
        hit = by_dir[p.parent].get(key)
        if hit:
            m = TrackMetrics(**hit)
            m.file = str(p)
        else:
            m = extract_metrics(p)
            by_dir[p.parent][key] = asdict(m)
            dirty.add(p.parent)
        out.append(m)
    for d in dirty:
        try:
            (d / CACHE_NAME).write_text(json.dumps(by_dir[d], indent=1), encoding="utf-8")
        except OSError:
            pass  # cache best-effort
    return out


def average(metrics: list[TrackMetrics]) -> TrackMetrics:
    if not metrics:
        raise ValueError("Nessun reference fornito")
    n = len(metrics)
    mean = lambda attr: float(np.mean([getattr(m, attr) for m in metrics]))  # noqa: E731
    return TrackMetrics(
        file=f"<media di {n} reference>",
        lufs=round(mean("lufs"), 2),
        lra=round(mean("lra"), 2),
        true_peak_dbtp=round(mean("true_peak_dbtp"), 2),
        crest_factor_db=round(mean("crest_factor_db"), 2),
        stereo_width=round(mean("stereo_width"), 3),
        bands={b: round(float(np.mean([m.bands.get(b, 0.0) for m in metrics])), 4) for b in BANDS},
    )


# --- Raccomandazioni -------------------------------------------------------

def recommendations(deltas: dict[str, float], band_deltas: dict[str, float],
                    mix_true_peak: float | None = None) -> list[str]:
    """Delta -> azioni concrete, in italiano. Bande con logica ratio-aware."""
    recs: list[str] = []
    tol = TOLERANCES

    d = deltas["lufs"]
    if abs(d) > tol["lufs"]:
        if d < 0:
            recs.append(f"LUFS {d:.1f} LU sotto reference: alza gain di {-d:.1f} dB "
                        f"o spingi il limiter (riduci threshold).")
        else:
            recs.append(f"LUFS {d:+.1f} LU sopra reference: stai esagerando con il limiting, "
                        f"rischio fatica e distorsione, abbassa di {d:.1f} dB.")

    d = deltas["lra"]
    if abs(d) > tol["lra"]:
        if d < 0:
            recs.append(f"LRA {abs(d):.1f} LU piu' stretto del reference: mix troppo compresso, "
                        f"allenta il bus comp (ratio o threshold).")
        else:
            recs.append(f"LRA {d:.1f} LU piu' largo del reference: dinamica eccessiva, "
                        f"comprimi di piu' o usa upward compression sui passaggi quieti.")

    tp_flag = deltas["true_peak"] > tol["true_peak"]
    if mix_true_peak is not None and mix_true_peak > TP_ABS_LIMIT:
        tp_flag = True
    if tp_flag:
        where = f" (mix a {mix_true_peak:+.1f} dBTP)" if mix_true_peak is not None else ""
        recs.append(f"True peak {deltas['true_peak']:+.1f} dB vs reference{where}: rischio "
                    f"inter-sample clipping, limiter true-peak con ceiling -1.0 dBTP "
                    f"(-0.3 se va solo in club).")

    d = deltas["crest_factor"]
    if d < -tol["crest_factor"]:
        recs.append(f"Crest factor {abs(d):.1f} dB sotto reference: transienti appiattiti, "
                    f"il punch del kick e' andato, rivaluta limiting/clipping pre-master.")

    d = deltas["stereo_width"]
    if abs(d) > tol["stereo_width"]:
        if d < 0:
            recs.append(f"Stereo width {abs(d):.2f} sotto reference: mix troppo centrato, "
                        f"allarga synth/atmosfere (sopra ~150 Hz) o controlla la fase.")
        else:
            recs.append(f"Stereo width {d:.2f} sopra reference: rischio mono compatibility, "
                        f"verifica in mono che il mix non collassi.")

    # Ratio-aware: coppie adiacenti con delta opposti che si compensano
    names = list(BANDS)
    handled: set[str] = set()
    for a, b in zip(names, names[1:]):
        da, db = band_deltas[a], band_deltas[b]
        opposite = (da > 0) != (db > 0)
        both = abs(da) > tol["band_ratio"] and abs(db) > tol["band_ratio"]
        cancel = abs(da + db) < 0.5 * min(abs(da), abs(db))
        if opposite and both and cancel and not (handled & {a, b}):
            excess, missing = (a, b) if da > 0 else (b, a)
            lo_m, hi_m = BANDS[missing]
            lo_e, hi_e = BANDS[excess]
            recs.append(
                f"Bilanciamento {excess}/{missing} sbilanciato verso {excess} "
                f"({band_deltas[excess] * 100:+.1f}% vs {band_deltas[missing] * 100:+.1f}%): "
                f"aggiungi energia in {missing} ({lo_m:.0f}-{hi_m:.0f} Hz) con saturazione armonica "
                f"o EQ shelf. NON tagliare {excess} ({lo_e:.0f}-{hi_e:.0f} Hz), perderesti fondazione.")
            handled |= {a, b}

    for band, d in band_deltas.items():
        if band in handled or abs(d) <= tol["band_ratio"]:
            continue
        lo, hi = BANDS[band]
        if d > 0:
            recs.append(f"Banda {band} ({lo:.0f}-{hi:.0f} Hz) +{d * 100:.1f}% vs reference: "
                        f"taglia con EQ shelf/bell in quella zona.")
        else:
            recs.append(f"Banda {band} ({lo:.0f}-{hi:.0f} Hz) {d * 100:.1f}% vs reference: "
                        f"manca energia, aggiungi con EQ shelf o saturazione armonica.")

    if not recs:
        recs.append("Mix entro tolleranze del reference set: pronto per il master finale.")
    return recs


def compare_metrics(mix: TrackMetrics, refs: list[TrackMetrics]) -> ComparisonReport:
    avg = average(refs)
    deltas = {
        "lufs": round(mix.lufs - avg.lufs, 2),
        "lra": round(mix.lra - avg.lra, 2),
        "true_peak": round(mix.true_peak_dbtp - avg.true_peak_dbtp, 2),
        "crest_factor": round(mix.crest_factor_db - avg.crest_factor_db, 2),
        "stereo_width": round(mix.stereo_width - avg.stereo_width, 3),
    }
    band_deltas = {b: round(mix.bands[b] - avg.bands[b], 4) for b in BANDS}
    return ComparisonReport(
        mix=mix,
        reference_files=[r.file for r in refs],
        reference_avg=avg,
        deltas=deltas,
        band_deltas=band_deltas,
        recommendations=recommendations(deltas, band_deltas, mix.true_peak_dbtp),
    )


def compare(mix_path: Path, reference_paths: list[Path], use_cache: bool = True) -> ComparisonReport:
    if not reference_paths:
        raise ValueError("Lista reference vuota")
    refs = cached_metrics(reference_paths) if use_cache else [extract_metrics(p) for p in reference_paths]
    return compare_metrics(extract_metrics(Path(mix_path)), refs)


# --- Output ----------------------------------------------------------------

def format_report(r: ComparisonReport) -> str:
    rows = [
        ("LUFS", r.mix.lufs, r.reference_avg.lufs, r.deltas["lufs"], "+9.2f"),
        ("LRA", r.mix.lra, r.reference_avg.lra, r.deltas["lra"], "+9.2f"),
        ("True peak dBTP", r.mix.true_peak_dbtp, r.reference_avg.true_peak_dbtp, r.deltas["true_peak"], "+9.2f"),
        ("Crest factor dB", r.mix.crest_factor_db, r.reference_avg.crest_factor_db, r.deltas["crest_factor"], "+9.2f"),
        ("Stereo width", r.mix.stereo_width, r.reference_avg.stereo_width, r.deltas["stereo_width"], "+9.3f"),
    ]
    lines = [f"{'metrica':<16}{'mix':>9}{'ref':>9}{'delta':>9}"]
    lines += [f"{n:<16}{m:>9}{a:>9}{d:{f}}" for n, m, a, d, f in rows]
    lines.append("")
    lines.append(f"{'banda':<16}{'mix %':>9}{'ref %':>9}{'delta':>9}")
    for b in BANDS:
        lines.append(f"{b:<16}{r.mix.bands[b] * 100:>9.2f}{r.reference_avg.bands[b] * 100:>9.2f}"
                     f"{r.band_deltas[b] * 100:>+9.2f}")
    lines.append("")
    lines.append("Raccomandazioni:")
    lines += [f"  {i}. {t}" for i, t in enumerate(r.recommendations, 1)]
    return "\n".join(lines)


def write_report(r: ComparisonReport, name: str, out_dir: Path | None = None) -> Path:
    out_dir = Path(out_dir or OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = out_dir / f"reference_{Path(name).stem}_{ts}.json"
    out.write_text(json.dumps(asdict(r), indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def _capture_loopback(seconds: float, sr: int = 48000) -> np.ndarray:
    """Uscita reale di Live in STEREO (serve per la stereo width)."""
    import soundcard as sc
    spk = sc.default_speaker()
    mic = sc.get_microphone(id=str(spk.name), include_loopback=True)
    with mic.recorder(samplerate=sr, channels=2) as rec:
        return rec.record(numframes=int(seconds * sr)).astype(np.float32)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m livemind.audio.reference",
                                 description="Confronta un mix con reference dello stesso genere.")
    ap.add_argument("mix", nargs="?", help="file audio del mix (oppure --loopback)")
    ap.add_argument("--genre", "-g", help=f"cartella in {REFS_DIR}")
    ap.add_argument("--refs", nargs="+", help="file reference espliciti")
    ap.add_argument("--loopback", type=float, metavar="SEC", help="cattura SEC secondi dall'uscita di Live")
    ap.add_argument("--no-cache", action="store_true", help="rimisura i reference")
    a = ap.parse_args(argv)

    if a.refs:
        refs = [Path(p) for p in a.refs]
    elif a.genre:
        refs = genre_refs(a.genre)
        if not refs:
            print(f"Nessun reference per '{a.genre}' in {REFS_DIR}. "
                  f"Generi disponibili: {', '.join(available_genres()) or 'nessuno'}", file=sys.stderr)
            return 1
    else:
        print("Specifica --genre o --refs", file=sys.stderr)
        return 1

    if a.loopback:
        sr = 48000
        x = _capture_loopback(a.loopback, sr)
        name = "loopback"
        mix = metrics_from_array(x, sr, name)
    elif a.mix:
        name = a.mix
        mix = extract_metrics(Path(a.mix))
    else:
        print("Serve un file mix oppure --loopback SEC", file=sys.stderr)
        return 1

    ref_m = [extract_metrics(p) for p in refs] if a.no_cache else cached_metrics(refs)
    report = compare_metrics(mix, ref_m)
    print(format_report(report))
    out = write_report(report, name)
    print(f"\nReport: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
