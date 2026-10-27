"""Genera preset KICK 3 tribe/hardtek partendo dal pack TRIBE_machines.

Perche' quella base: un kick di KICK 3 che suona usa DUE layer — Slot1 con un
campione di click (l'attacco, contenuto nel blob <DATA> del preset) e Slot2 con
il sub sintetizzato. Il pack TRIBE_analog aveva Slot1 spento: solo sub, nessun
attacco, per questo non suonava. Partendo da TRIBE_machines ereditiamo il
campione di click gia' incorporato e modelliamo solo il sub e le durate.

Le curve vere non sono nei PARAM ma negli elementi <SlotN_AmpEnvelope> /
<SlotN_PitchEnvelope> (vedi kick3_env).

Uso:  python -m livemind.presets.make_tribe_kick [nome] [base]
"""
from __future__ import annotations
import sys
from pathlib import Path

from livemind.presets.kick3 import get_param, set_param
from livemind.presets.kick3_env import set_envelope

from livemind.paths import KICK3_PRESETS as K3_USER  # override: LIVEMIND_KICK3_PRESETS
BASE = K3_USER / "TRIBE_machines" / "02 TRIBE 909.preset"
OUT_DIR = K3_USER / "LIVEMIND Tribe"

# --- Durate -------------------------------------------------------------
# A 150 BPM il quarto dura 400 ms. Il sub a 430 ms lascia la coda appena
# sovrapposta al colpo successivo: e' la spinta continua del tribe, senza
# arrivare al fango di una coda da 700 ms.
# --- Ampiezza (tempi in MILLISECONDI, convertiti in x sulla lunghezza reale)
# Curvatura negativa: caduta rapida subito dopo l'attacco e poi coda che si
# allunga, invece di una rampa lineare che suona meccanica.
# La curvatura pesa molto: a -0.35 il corpo moriva in 150 ms invece di 430.
# Curve quasi lineari + un ultimo segmento corto verso lo zero: senza
# quest'ultimo l'envelope si chiude di scatto e si sente un click di taglio.
SUB_AMP_MS = [
    (0.0,   1.00, 0.0),
    (60.0,  0.86, 0.0),    # plateau breve: allunga il corpo senza perdere punch
    (200.0, 0.58, 0.0),
    (350.0, 0.28, 0.0),
    (455.0, 0.06, 0.0),
    (480.0, 0.00, 0.0),    # ultimo tratto verso zero: evita il click di taglio
]
CLICK_AMP_MS = [
    (0.0,   1.00, -0.50),
    (25.0,  0.25, -0.30),
    (85.0,  0.00, 0.0),
    (480.0, 0.00, 0.0),
]

# --- Pitch del sub ------------------------------------------------------
# y=1.0 e' il pitch di base (nodo keytracked). La discesa parte sopra e
# scende: e' il "boing" tribe. Tenuta breve (i primi 12% dei 150 ms) per
# non trasformarla in un tom.
SUB_PITCH_MS = [
    (0.0,   1.00, -0.45),
    (12.0,  0.42, -0.35),
    (40.0,  0.16, 0.0),
    (100.0, 0.14, 0.0),
]

SUB_HARMONICS = [100, 22, 13, 7, 3, 0, 0, 0]
SUB_HARMO_DECAY = [0, 55, 68, 78, 85, 0, 0, 0]
SUB_GAIN_DB = -5.0
PITCH_SEMI = 0.0


# Verificato caricando due preset e guardando quale curva compare nella UI:
# il layer "Clicks" e' Slot1, il "Sub" e' Slot2. (Conferma incrociata: il pack
# TRIBE_analog aveva solo Slot2 attivo ed era senza attacco = solo sub.)
SLOT_CLICK = 1
SLOT_SUB = 2


def _len_of(xml: str, pid: str, fallback: float) -> float:
    """La lunghezza dell'envelope NON e' modificabile dai PARAM: il plugin la
    legge dal blob <DATA>. Quindi la si prende com'e' e ci si adatta,
    convertendo i tempi in millisecondi nella x normalizzata corrispondente."""
    try:
        return float(get_param(xml, pid, fallback))
    except (TypeError, ValueError):
        return fallback


def _to_x(points_ms, total_ms: float):
    """(ms, y[, curvatura]) -> (x normalizzato, y[, curvatura]), clampato a 1."""
    out = []
    for p in points_ms:
        x = min(p[0] / total_ms, 1.0)
        out.append((round(x, 5),) + tuple(p[1:]))
    return out


def build(xml: str) -> str:
    sub_len = _len_of(xml, f"Slot{SLOT_SUB}AmpEnvMaxLen", 480.0)
    click_len = _len_of(xml, f"Slot{SLOT_CLICK}AmpEnvMaxLen", 480.0)
    pitch_len = _len_of(xml, f"Slot{SLOT_SUB}PitchEnvRangeMax", 100.0)

    xml = set_param(xml, f"Slot{SLOT_SUB}Type", 2.0)
    xml = set_param(xml, f"Slot{SLOT_CLICK}Type", 1.0)
    xml = set_param(xml, f"Slot{SLOT_SUB}PitchSemi", PITCH_SEMI)
    xml = set_param(xml, f"Slot{SLOT_SUB}Gain", SUB_GAIN_DB)

    xml = set_envelope(xml, f"Slot{SLOT_SUB}_AmpEnvelope",
                       _to_x(SUB_AMP_MS, sub_len))
    xml = set_envelope(xml, f"Slot{SLOT_CLICK}_AmpEnvelope",
                       _to_x(CLICK_AMP_MS, click_len))
    xml = set_envelope(xml, f"Slot{SLOT_SUB}_PitchEnvelope",
                       _to_x(SUB_PITCH_MS, pitch_len), keytracked=1)

    for i, (amp, dec) in enumerate(zip(SUB_HARMONICS, SUB_HARMO_DECAY), start=1):
        xml = set_param(xml, f"Slot{SLOT_SUB}SubHarmo{i:02d}", amp)
        xml = set_param(xml, f"Slot{SLOT_SUB}SubDecay{i:02d}", dec)
    return xml


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "TRIBE 150 - LM01"
    base = Path(sys.argv[2]) if len(sys.argv) > 2 else BASE
    if not base.exists():
        raise SystemExit(f"preset base mancante: {base}")
    out = build(base.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = OUT_DIR / f"{name}.preset"
    dest.write_text(out, encoding="utf-8")
    print(f"scritto: {dest}  (base: {base.name})")


if __name__ == "__main__":
    main()
