"""Carica un file .preset in KICK 3 dal menu 'Load Preset'.

Piu' robusto del browser interno: il menu apre un dialogo file di Windows, in
cui si puo' incollare il percorso completo. Non dipende dalla posizione delle
bank nella lista ne' dalla dimensione della finestra del plugin.

Uso:  python -m livemind.presets.kick3_load "C:\\...\\TRIBE 150 - LM01.preset"
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

MENU_BTN = (191, 80)     # hamburger, offset dalla finestra del plugin
MENU_LOAD = (233, 128)   # voce "Load Preset"


def window():
    import pygetwindow as gw
    for w in gw.getAllWindows():
        if "kick 3" in w.title.lower():
            return w
    return None


def load(path: str, shot: str | None = None) -> str:
    import pyautogui
    p = Path(path)
    if not p.exists():
        return f"preset non trovato: {p}"
    w = window()
    if w is None:
        return "finestra di KICK 3 non aperta (usare la chiave inglese sul device)"
    try:
        w.activate()
    except Exception:
        pass
    time.sleep(1.0)
    pyautogui.click(w.left + MENU_BTN[0], w.top + MENU_BTN[1])
    time.sleep(1.2)
    pyautogui.click(w.left + MENU_LOAD[0], w.top + MENU_LOAD[1])
    time.sleep(2.2)
    pyautogui.write(str(p), interval=0.01)
    time.sleep(0.4)
    pyautogui.press("enter")
    time.sleep(2.2)
    if shot:
        pyautogui.screenshot(shot, region=(w.left, w.top, w.width, w.height))
    return f"caricato: {p.name}" + (f" | shot={shot}" if shot else "")


if __name__ == "__main__":
    print(load(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
