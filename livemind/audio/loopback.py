"""Cattura l'uscita reale di Live (loopback WASAPI) e la rende leggibile.

Il MasterAnalyzer registra da un dispositivo di INPUT: se non esiste un cavo
virtuale sente silenzio. Qui si registra direttamente dal dispositivo di
uscita in modalita' loopback, che su Windows e' nativo (WASAPI) e non richiede
driver aggiuntivi.

Oltre alle misure numeriche produce un PNG con forma d'onda e spettrogramma:
un modello non puo' ascoltare, ma puo' guardare l'immagine e riconoscere
maschera tra kick e basso, code troppo lunghe, buchi nei medi.

Uso:  python -m livemind.audio.loopback [secondi] [nome]
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "bridge" / "audio"


def capture(seconds: float = 6.0, samplerate: int = 48000) -> np.ndarray:
    """Registra l'uscita del dispositivo di default. Ritorna mono float32."""
    import soundcard as sc
    spk = sc.default_speaker()
    mic = sc.get_microphone(id=str(spk.name), include_loopback=True)
    with mic.recorder(samplerate=samplerate, channels=2) as rec:
        data = rec.record(numframes=int(seconds * samplerate))
    return data.mean(axis=1).astype(np.float32)


def measure(x: np.ndarray, sr: int = 48000) -> dict:
    from livemind.audio.analyzer import integrated_lufs, true_peak_dbtp, spectral_balance
    return {
        "lufs_integrated": round(float(integrated_lufs(x, sr)), 2),
        "true_peak_dbtp": round(float(true_peak_dbtp(x, sr)), 2),
        "spectral_balance_db": {k: round(float(v), 1)
                                 for k, v in spectral_balance(x, sr).items()},
    }


def render_png(x: np.ndarray, sr: int, dest: Path) -> Path:
    """Forma d'onda + spettrogramma log, pensati per essere GUARDATI."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), height_ratios=[1, 2])
    t = np.arange(len(x)) / sr
    ax1.plot(t, x, linewidth=0.4, color="#00e5a0")
    ax1.set_xlim(0, t[-1] if len(t) else 1)
    ax1.set_ylabel("ampiezza")
    ax1.grid(alpha=0.2)

    # nperseg piccolo: sul kick conta la risoluzione TEMPORALE del transiente,
    # non quella in frequenza
    ax2.specgram(x, NFFT=1024, Fs=sr, noverlap=768, cmap="magma",
                 vmin=-120, vmax=-20)
    ax2.set_yscale("symlog", linthresh=100)
    ax2.set_ylim(20, sr / 2)
    ax2.set_ylabel("Hz")
    ax2.set_xlabel("secondi")
    for hz in (50, 100, 200, 500, 1000, 5000):
        ax2.axhline(hz, color="white", alpha=0.15, linewidth=0.6)

    fig.tight_layout()
    dest.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(dest, dpi=90)
    plt.close(fig)
    return dest


def main() -> None:
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    name = sys.argv[2] if len(sys.argv) > 2 else "capture"
    sr = 48000
    x = capture(seconds, sr)
    m = measure(x, sr)
    png = render_png(x, sr, OUT_DIR / f"{name}.png")
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    print(f"picco_lineare={peak:.4f}")
    print(m)
    print(f"png={png}")


if __name__ == "__main__":
    main()
