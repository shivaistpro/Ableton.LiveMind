"""DeviceLoader: carica device/VST dal browser di Live automatizzando la UI.

AbletonOSC non espone il browser, quindi: focus su Live -> Ctrl+F -> nome ->
Down -> Enter. Prima di caricare, selezionare la traccia destinazione via OSC.
Best-effort: richiede Live visibile e non in dialogo modale.
"""
from __future__ import annotations
import time

try:
    import pyautogui
    import pygetwindow as gw
    _HAS_UI = True
except Exception:  # pragma: no cover
    _HAS_UI = False


class DeviceLoader:
    def __init__(self, search_delay: float = 1.2):
        if not _HAS_UI:
            raise RuntimeError("pip install pyautogui pygetwindow")
        self.search_delay = search_delay

    def _focus_live(self) -> bool:
        wins = [w for w in gw.getAllWindows() if "ableton live" in w.title.lower()]
        if not wins:
            return False
        w = wins[0]
        # Windows blocca SetForegroundWindow da un processo in background
        # (anti focus-steal): activate() "riesce" (code 0) ma la finestra non
        # passa davvero avanti e i tasti vanno nel vuoto. minimize->restore
        # forza il vero foreground. Ogni step e' best-effort (pygetwindow
        # solleva eccezioni fasulle anche in caso di successo).
        for step in (
            (lambda: w.restore() if w.isMinimized else None),
            (lambda: w.minimize()),
            (lambda: w.restore()),
            (lambda: w.activate()),
        ):
            try:
                step()
            except Exception:
                pass
            time.sleep(0.25)
        return True

    def load(self, device_name: str) -> str:
        if not self._focus_live():
            return "ERRORE: finestra di Ableton Live non trovata"
        pyautogui.hotkey("ctrl", "f")          # focus ricerca browser
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "a")          # svuota una ricerca precedente
        pyautogui.press("delete")
        time.sleep(0.1)
        pyautogui.typewrite(device_name, interval=0.02)
        time.sleep(self.search_delay)           # attesa risultati (VST scan)
        pyautogui.press("down")                  # primo risultato
        time.sleep(0.15)
        pyautogui.press("enter")                 # carica sulla traccia selezionata
        time.sleep(0.3)
        pyautogui.press("esc")                   # esci dalla ricerca
        return f"caricato (primo risultato browser per '{device_name}')"
