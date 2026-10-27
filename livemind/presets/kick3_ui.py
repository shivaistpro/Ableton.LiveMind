"""Pilota la UI di KICK 3 per caricare un preset senza intervento umano.

Il browser interno di KICK 3 non e' esposto alla LOM (Live vede il VST come un
device con un solo parametro), quindi l'unica via e' il mouse. Le coordinate
sono espresse come FRAZIONI della finestra del plugin, non in pixel assoluti:
cosi' restano valide se la finestra viene spostata o ridimensionata.

Ogni azione salva uno screenshot in bridge/audio/: serve a verificare con gli
occhi che il click sia finito dove doveva, invece di sperarlo.

Uso:  python -m livemind.presets.kick3_ui load "LIVEMIND Tribe" 0
      python -m livemind.presets.kick3_ui shot
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

SHOT_DIR = Path(__file__).resolve().parent.parent.parent / "bridge" / "audio"
TITLE_HINT = "kick 3"

# frazioni (x, y) misurate sulla finestra del plugin
HAMBURGER = (0.148, 0.100)
TAB_USER = (0.358, 0.202)
BTN_RESCAN = (0.421, 0.202)
BANK_X = 0.245
BANK_Y0 = 0.309
BANK_DY = 0.0312
PRESET_X = 0.467
PRESET_Y0 = 0.3815
PRESET_DY = 0.0312

# ordine alfabetico delle bank come le mostra il browser
BANKS = ["_TEST_CALIBRAZIONE", "LIVEMIND Tribe", "TRIBE_analog",
         "TRIBE_machines", "User Presets"]


def _win():
    import pygetwindow as gw
    for w in gw.getAllWindows():
        if TITLE_HINT in w.title.lower():
            return w
    return None


def _click(w, fx: float, fy: float, pause: float = 0.45) -> tuple[int, int]:
    import pyautogui
    x = int(w.left + fx * w.width)
    y = int(w.top + fy * w.height)
    pyautogui.click(x, y)
    time.sleep(pause)
    return x, y


def shot(name: str = "kick3_ui") -> str:
    import pyautogui
    w = _win()
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    dest = SHOT_DIR / f"{name}.png"
    region = (w.left, w.top, w.width, w.height) if w else None
    pyautogui.screenshot(str(dest), region=region)
    return str(dest)


def load_preset(bank: str, preset_index: int = 0, rescan: bool = True) -> str:
    w = _win()
    if w is None:
        return "finestra di KICK 3 non trovata (aprire il plugin in Live)"
    if bank not in BANKS:
        return f"bank sconosciuta: {bank} (attese: {BANKS})"
    try:
        w.activate()
    except Exception:
        pass
    time.sleep(0.5)

    steps = []
    steps.append(("hamburger", _click(w, *HAMBURGER, pause=0.7)))
    steps.append(("tab User", _click(w, *TAB_USER)))
    if rescan:
        # la cartella User viene riletta solo su richiesta: senza Rescan una
        # bank appena creata non compare
        steps.append(("rescan", _click(w, *BTN_RESCAN, pause=1.2)))
        steps.append(("tab User", _click(w, *TAB_USER)))
    row = BANKS.index(bank)
    steps.append((f"bank {bank}", _click(w, BANK_X, BANK_Y0 + row * BANK_DY, pause=0.6)))
    steps.append((f"preset #{preset_index}",
                  _click(w, PRESET_X, PRESET_Y0 + preset_index * PRESET_DY, pause=0.8)))
    png = shot("kick3_after_load")
    return "; ".join(f"{n}@{p}" for n, p in steps) + f" | screenshot={png}"


def dispatch(args: dict) -> str:
    a = args.get("action", "load")
    if a == "shot":
        return shot(args.get("name", "kick3_ui"))
    if a == "load":
        return load_preset(args["bank"], int(args.get("preset_index", 0)),
                           bool(args.get("rescan", True)))
    return f"azione kick3_ui sconosciuta: {a}"


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "shot":
        print(shot(sys.argv[2] if len(sys.argv) > 2 else "kick3_ui"))
    else:
        print(load_preset(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 0))
