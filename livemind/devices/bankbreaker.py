"""Controllo completo di BankBreaker via LOM.

BankBreaker e' un JUCE/APVTS, quindi Live espone TUTTI i suoi parametri come
device parameter automatizzabili — al contrario di KICK 3, che ne espone uno
solo. Si puo' quindi pilotare interamente dal canale LOM, senza toccare la UI.

La mappa qui sotto e' ricavata dal sorgente (createParameterLayout), non da
tentativi: nomi esatti come li vede Live, range reali e voci degli enum.

I valori nella LOM sono nell'unita' NATIVA del parametro (Hz, ms, indice
dell'enum), non normalizzati 0-1.
"""
from __future__ import annotations
import math

DRIVE_TYPES = ["Tube", "Tape", "Fuzz", "Bitcrush", "Foldback", "FoldAsym",
               "Saturator", "Transformer", "Diode", "CMOS"]
FILTER_MODES = ["LP", "BP", "HP", "Notch"]
LFO_DIVS = ["Free", "2 bars", "1 bar", "1/2", "1/4", "1/8", "1/16", "1/32"]
ENV_RANGES = ["Off", "Quint", "Octave", "Wide"]
KBD_TRACK = ["Track", "Track Low"]
OVERSAMPLE = ["Off", "2x", "4x"]

# nome visibile in Live -> (minimo, massimo, default, unita'/enum)
PARAMS: dict[str, tuple] = {
    "F1 Cutoff":       (20.0, 18000.0, 800.0, "Hz"),
    "F1 Reso":         (0.0, 1.0, 0.5, ""),
    "F1 Mode":         (0, 3, 1, FILTER_MODES),
    "F2 Cutoff":       (20.0, 18000.0, 2000.0, "Hz"),
    "F2 Reso":         (0.0, 1.0, 0.5, ""),
    "F2 Mode":         (0, 3, 1, FILTER_MODES),
    "Drive":           (0.0, 1.0, 0.2, ""),
    "Drive Type":      (0, 9, 0, DRIVE_TYPES),
    "Character":       (0.0, 1.0, 0.0, ""),
    "LFO Rate":        (0.05, 30.0, 1.0, "Hz"),
    "LFO Depth":       (0.0, 1.0, 0.0, ""),
    "LFO Sync":        (0, 1, 0, "bool"),
    "LFO Div":         (0, 7, 4, LFO_DIVS),
    "AM Depth":        (0.0, 1.0, 0.0, ""),
    "FM Depth":        (0.0, 1.0, 0.0, ""),
    "Env Attack":      (0.5, 200.0, 10.0, "ms"),
    "Env Decay":       (1.0, 1000.0, 100.0, "ms"),
    "Env Sustain":     (0.0, 1.0, 1.0, ""),
    "Env Release":     (5.0, 2000.0, 200.0, "ms"),
    "Env Depth":       (-1.0, 1.0, 0.0, ""),
    "Env Hold":        (0, 1, 0, "bool"),
    "F1<>F2 Mix":      (0.0, 1.0, 0.5, ""),
    "Routing":         (0, 1, 0, ["Parallel", "Serial F1->F2"]),
    "Dry/Wet":         (0.0, 1.0, 1.0, ""),
    "Out Gain":        (0.0, 2.0, 1.0, ""),
    "Key Track":       (0.0, 1.0, 0.0, ""),
    "Velocity Amt":    (-1.0, 1.0, 0.0, ""),
    "Pitch Bend Amt":  (-1.0, 1.0, 0.0, ""),
    "Aftertouch Amt":  (-1.0, 1.0, 0.0, ""),
    "Oversample":      (0, 2, 0, OVERSAMPLE),
    "Reso Drive":      (0.0, 1.0, 0.0, ""),
    "Reso Drive Type": (0, 9, 0, DRIVE_TYPES),
    "Bloom":           (0.0, 1.0, 0.0, ""),
    "Hi Cut":          (0, 1, 0, "bool"),
    "Env Sensitivity": (0.0, 3.0, 1.0, ""),
    "Env Limit":       (0, 1, 0, "bool"),
    "Env Range":       (0, 3, 3, ENV_RANGES),
    "Key Track Mode":  (0, 1, 0, KBD_TRACK),
}


# Parametri con range "skewed" nel sorgente (setSkewForCentre): la posizione
# 0.5 del knob non sta a meta' del range ma sul valore centrale indicato.
SKEW_CENTRE = {
    "F1 Cutoff": 600.0,      # sqrt(20*18000)
    "F2 Cutoff": 600.0,
    "LFO Rate": 1.0,
    "Env Attack": 10.0,
    "Env Decay": 100.0,
    "Env Release": 200.0,
}


def to_norm(param: str, value) -> float:
    """Valore in unita' native -> 0..1 come lo vuole Live.

    Live espone i parametri di un VST SEMPRE normalizzati: scrivere 220 su un
    cutoff in Hz non imposta 220 Hz, viene rifiutato. Qui si replica la
    NormalisableRange di JUCE, skew compreso
    (convertTo0to1: ((v-lo)/(hi-lo)) ** skew).
    """
    lo, hi, _, kind = PARAMS[param]
    if isinstance(kind, list):                      # enum: indice -> frazione
        return min(max(float(value), 0.0), len(kind) - 1) / (len(kind) - 1)
    if kind == "bool":
        return 1.0 if value else 0.0
    v = min(max(float(value), lo), hi)
    prop = (v - lo) / (hi - lo)
    centre = SKEW_CENTRE.get(param)
    if centre is not None and 0.0 < prop < 1.0:
        skew = math.log(0.5) / math.log((centre - lo) / (hi - lo))
        prop = prop ** skew
    return prop


def enum_value(param: str, label: str) -> int:
    """Indice di una voce di enum a partire dall'etichetta ('Diode' -> 8)."""
    spec = PARAMS.get(param)
    if not spec or not isinstance(spec[3], list):
        raise KeyError(f"{param} non e' un enum")
    return spec[3].index(label)


def clamp(param: str, value):
    lo, hi = PARAMS[param][0], PARAMS[param][1]
    return max(lo, min(hi, value))


# --- Preset per il kick tribe -------------------------------------------
# Non un filtro "che filtra": qui BankBreaker fa da distorsore armonico.
# - Drive Type Transformer: satura i bassi senza assottigliarli come Fuzz
# - F1 in BP largo sui medi bassi: e' li' che nasce il growl tribe
# - Reso Drive + Bloom: il loop risonante che allunga la coda con armoniche
#   invece che con volume, cosi' il kick "palleggia" invece di impastarsi
# - Env Depth negativo: il filtro si chiude sul transiente e riapre subito
#   dopo, dando il movimento senza sporcare l'attacco
TRIBE_DIST = {
    # Fuzz: molto piu' aggressivo del Transformer e assottiglia i bassi, quindi
    # drive piu' basso e piu' segnale asciutto (Dry/Wet) per non perdere il
    # fondamentale sotto la distorsione.
    "Drive": 0.34,
    "Drive Type": DRIVE_TYPES.index("Fuzz"),
    "Character": 0.24,
    # LP risonante, NON band-pass: un BP a 220 Hz in serie attenua sotto la
    # frequenza e si mangia il fondamentale a 52 Hz (misurato: sub da -33.9 a
    # -44.2 dB). Con l'LP il basso passa intero e la risonanza da' il growl.
    "F1 Mode": FILTER_MODES.index("LP"),
    "F1 Cutoff": 260.0,
    # Reso 0.45 insieme a Reso Drive alto mandava il loop in auto-oscillazione:
    # bande fisse a 180/400/600 Hz che suonavano anche tra un colpo e l'altro.
    "F1 Reso": 0.30,
    "F2 Mode": FILTER_MODES.index("LP"),
    "F2 Cutoff": 3500.0,
    "F2 Reso": 0.18,
    "Routing": 0,           # parallelo: i due filtri sommano, non si sottraggono
    "F1<>F2 Mix": 0.5,
    # Sotto la soglia di auto-oscillazione: la coda si allunga di armoniche
    # ma muore, cosi' il kick respira invece di lasciare un drone.
    # Bloom alzato: la finestra dell'envelope del Sub in KICK 3 e' fissa
    # (~170 ms, sta nel blob DATA e non e' scrivibile), quindi la coda si
    # allunga qui, con la risonanza. Con F1 Reso a 0.30 c'e' margine prima
    # dell'auto-oscillazione (che partiva a Bloom 0.35 con Reso 0.45).
    "Reso Drive": 0.22,
    "Reso Drive Type": DRIVE_TYPES.index("Diode"),
    "Bloom": 0.30,
    "Env Attack": 3.0,
    "Env Decay": 180.0,
    "Env Sustain": 0.0,
    "Env Release": 260.0,
    "Env Depth": -0.28,
    "Env Sensitivity": 1.4,
    "Env Range": ENV_RANGES.index("Octave"),
    "Oversample": OVERSAMPLE.index("2x"),   # c'e' distorsione: serve contro l'aliasing
    # Dry/Wet non a 1: una quota di segnale asciutto tiene il fondamentale
    # pulito sotto la distorsione. Out Gain compensa i ~10 dB persi nei filtri.
    "Dry/Wet": 0.58,
    "Out Gain": 1.12,   # -0.09 dBTP era troppo caldo: target <= -1 dBTP
}


def apply(track: int, device: int, values: dict | None = None, verbose: bool = True) -> dict:
    """Applica un dizionario {nome parametro: valore} via LOM.

    Cerca per NOME e non per indice: l'ordine dei parametri di un VST non e'
    garantito tra versioni. Ritorna quel che ha scritto, con il valore che il
    plugin mostra davvero (display_value) — cosi' si vede subito se un valore
    e' stato clampato o interpretato in un'altra unita'.
    """
    from livemind.lom_client import LomClient
    lom = LomClient(timeout=15.0)
    base = [f"tracks:{track}", f"devices:{device}"]
    n = int(lom.length(base + ["parameters"]).get("value", 0) or 0)
    index = {}
    for i in range(n):
        nm = lom.get(base + [f"parameters:{i}"], "name").get("value")
        if nm:
            index[nm] = i

    out, missing = {}, []
    for name, val in (values if values is not None else TRIBE_DIST).items():
        i = index.get(name)
        if i is None:
            missing.append(name)
            continue
        lom.set(base + [f"parameters:{i}"], "value", to_norm(name, val))
        shown = lom.get(base + [f"parameters:{i}"], "display_value").get("value")
        out[name] = shown
        if verbose:
            print(f"{name} = {shown}")
    if missing:
        print("NON TROVATI:", ", ".join(missing))
        print("disponibili:", ", ".join(sorted(index)))
    return out


def commands(track: int, device: int, values: dict | None = None) -> list[dict]:
    """Genera i comandi bridge 'set_param_by_name' per applicare un preset.
    Cerca per NOME: l'indice dei parametri di un VST non e' garantito."""
    values = values if values is not None else TRIBE_DIST
    out = []
    for name, val in values.items():
        out.append({"tool": "set_param_by_name",
                    "args": {"track": track, "device": device,
                             "param_name": name, "value": val}})
    return out
