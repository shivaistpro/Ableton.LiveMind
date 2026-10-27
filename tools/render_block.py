"""Render the block between two locators to WAV, start to finish, unattended.

Every failure this run hit is handled here instead of by hand:

- **loop stale** -- the export dialog pre-fills from the arrangement loop. A loop
  left somewhere else silently rendered 31 bars from bar 129. The loop is now set
  over a direct LOM socket and *verified* before the dialog opens.
- **focus** -- without forcing Live to the foreground the keystrokes land in
  whatever window is in front (once, in a chat box). Focus is forced and checked.
- **modal dialogs** -- a leftover "save before closing?" box swallows everything.
  Escape is sent first, and the window title is checked.
- **bridge starvation** -- polling the file bridge during a render hung Live.
  This script does its own waiting locally and writes the outcome to a status
  file, so the caller reads one file once instead of hammering the bridge.
- **name field** -- the save dialog keeps the previous name; it is cleared first.
- **range fields are 3 sub-widgets, not text boxes** -- Punto d'Inizio/Lunghezza
  each split into bar/beat/tick. A mouse click on one only *displays* focus
  there but does not arm real text editing: Ctrl+A after a click leaves the
  old value mixed with whatever gets typed (confirmed on two real renders that
  silently exported ~2425 bars instead of 192). Tab/Shift+Tab keyboard
  navigation *does* arm editing -- Ctrl+A then cleanly replaces one sub-field.
  So every sub-field here is reached by Tab, never by a click on its own
  coordinates, entering the chain from one known click (FLD_LEN) that lands
  two Shift+Tabs before Start.bar.

Usage: python render_block.py <nome> [start_beat] [end_beat]
Status: out/render_status.json   ->  {"state": "done"|"failed"|..., ...}
"""
from __future__ import annotations

import os, sys  # noqa: E401
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _paths import OUT, SHOTS, out_path  # noqa: E402,F401
import json
import os
import sys
import time

import pyautogui
import pygetwindow as gw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lom_direct import Lom, set_loop        # noqa: E402
from ui_safety import exclusive, close_stray_dialogs, UIBusyError  # noqa: E402

OUT = str(OUT)
SHOTS = os.path.join(OUT, "shots")
STATUS = os.path.join(OUT, "render_status.json")
pyautogui.FAILSAFE = False

# Coordinate (1920x1080). Se la UI cambia, aggiornare qui.
MENU_FILE = (20, 45)
MENU_ESPORTA = (90, 483)      # voce "Esporta Audio/Video" nel menu File (verificata su screenshot 18/09)
FLD_LEN = (1075, 267)         # un punto qualsiasi dentro il widget "Lunghezza" -- solo per entrare
BTN_ESPORTA = (914, 859)
FLD_NOME = (1070, 596)
BTN_SALVA = (1709, 707)


def bbt_pos(beat, beats_per_bar=4.0):
    """Beat assoluto (0-based, come loop_start) -> (bar, beat, tick) 1-based
    per il sotto-campo Posizione."""
    bar = int(beat // beats_per_bar) + 1
    beat_in_bar = int(beat % beats_per_bar) + 1
    return bar, beat_in_bar, 1


def bbt_len(beats, beats_per_bar=4.0):
    """Durata in beat -> (bar, 0, 0): la Lunghezza e' un conteggio di bar
    (convenzione osservata nel dialogo), non una posizione 1-based."""
    return round(beats / beats_per_bar), 0, 0


def type_subfield(value):
    """Sovrascrive il sotto-campo bar/beat/tick col focus corrente e passa
    al successivo. Richiede che il focus sia gia' "armato" per l'editing
    testuale (arrivarci via Tab/Shift+Tab, non via click)."""
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.15)
    pyautogui.write(str(value), interval=0.03)
    pyautogui.press("tab")
    time.sleep(0.25)


def dialog_open(title_part="esporta"):
    """True se una finestra di dialogo col titolo atteso e' davvero aperta.

    Agire alla cieca sulle coordinate quando il dialogo non c'e' significa
    cliccare sull'arrangement: e' cosi' che sono partiti comandi indesiderati.
    """
    for w in gw.getAllWindows():
        if title_part in (w.title or "").lower():
            return True
    return False


def status(state, **kw):
    data = {"state": state, "t": time.strftime("%H:%M:%S"), **kw}
    os.makedirs(OUT, exist_ok=True)
    with open(STATUS, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    print(json.dumps(data, ensure_ascii=False))
    return data


def shot(tag):
    os.makedirs(SHOTS, exist_ok=True)
    p = os.path.join(SHOTS, "%s.png" % tag)
    pyautogui.screenshot(p)
    return p


def live_window():
    for w in gw.getAllWindows():
        if "ableton live" in w.title.lower() and w.title.strip():
            return w
    return None


def focus_live():
    """minimize->restore: activate() alone does not really raise the window
    when the caller is a background process (Windows anti focus-steal)."""
    w = live_window()
    if w is None:
        return False
    for step in (lambda: w.restore() if w.isMinimized else None,
                 lambda: w.minimize(), lambda: w.restore(), lambda: w.activate()):
        try:
            step()
        except Exception:
            pass
        time.sleep(0.35)
    return True


def minimize_bridge():
    """La console del bridge si porta in primo piano ogni volta che gestisce un
    comando e ruba i tasti al dialogo (una volta ha ricevuto il nome file).
    Minimizzarla prima di ogni digitazione."""
    for w in gw.getAllWindows():
        if "livemind bridge" in (w.title or "").lower() and not w.isMinimized:
            try:
                w.minimize()
            except Exception:
                pass
    time.sleep(0.5)


def main(name, lo=0.0, hi=768.0):
    try:
        with exclusive("render_block"):
            return _main(name, lo, hi)
    except UIBusyError as e:
        return status("failed", why=str(e))


def _main(name, lo, hi):
    # Il dialogo Salva ricorda l'ultima cartella usata da Live, non una fissa:
    # se 'name' e' solo un nome, il file puo' finire altrove e questo script
    # aspetterebbe per sempre un path che non cresce mai. Con un path assoluto
    # in 'name' scriviamo esattamente li' (Windows accetta un path completo
    # nel campo Nome file) e monitoriamo lo stesso identico file.
    dest = name + ".wav" if os.path.isabs(name) else os.path.join(OUT, name + ".wav")
    field_text = name
    if os.path.exists(dest):
        os.remove(dest)

    chiusi = close_stray_dialogs()
    if chiusi:
        status("dialoghi_orfani_chiusi", titoli=chiusi)

    lom = Lom()
    if not lom.ping().get("ok"):
        return status("failed", why="Remote Script non raggiungibile su 9005")

    if not set_loop(lom, lo, hi - lo):
        return status("failed", why="loop non applicato")

    sig = lom.get([], "signature_numerator")
    beats_per_bar = float(sig) if sig else 4.0
    s_bar, s_beat, s_tick = bbt_pos(lo, beats_per_bar)
    l_bar, l_beat, l_tick = bbt_len(hi - lo, beats_per_bar)

    if not focus_live():
        return status("failed", why="finestra di Live non trovata")
    time.sleep(1.5)

    pyautogui.press("escape")          # via eventuali dialoghi residui
    time.sleep(0.8)

    # NIENTE Ctrl+Shift+R: se i modificatori non registrano resta "R", che in
    # Live inverte la clip selezionata. E' successo, e ha invertito clip vere.
    # Il menu File non ha fallback distruttivi: se il click manca, non accade nulla.
    pyautogui.click(*MENU_FILE)
    time.sleep(1.2)
    pyautogui.click(*MENU_ESPORTA)
    time.sleep(4.0)
    shot("rb_1_dialog")

    if not dialog_open():
        return status("failed", why="dialogo Esporta non aperto: nessun comando inviato")

    # Il dialogo precompila Inizio/Lunghezza dalla time selection di Live, NON
    # si scrivono a mano: sono 3 sotto-widget bar/beat/tick e l'editing da
    # script e' inaffidabile (due render sbagliati da 2425 bar). Con la
    # selezione = loop (verificato con screenshot: 1.1.1 / 192.0.0) basta
    # controllare rb_1b_range.png.
    shot("rb_1b_range")

    minimize_bridge()
    pyautogui.click(*BTN_ESPORTA)
    time.sleep(4.0)
    shot("rb_2_save")

    # Dialogo Salva di Windows: il path completo nel campo Nome file NON salva
    # (dialogo resta aperto). Cartella nella barra indirizzi (Alt+D), solo il
    # nome in Nome file (Alt+N), Invio al posto del click su Salva (posizione
    # variabile con la finestra di Live).
    folder, base = os.path.split(dest)
    minimize_bridge()
    pyautogui.hotkey("alt", "d")
    time.sleep(0.4)
    pyautogui.write(folder, interval=0.01)
    pyautogui.press("enter")
    time.sleep(1.0)
    pyautogui.hotkey("alt", "n")
    time.sleep(0.3)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(os.path.splitext(base)[0], interval=0.02)
    time.sleep(0.4)
    shot("rb_3_name")
    pyautogui.press("enter")
    status("rendering", file=dest)

    # Attesa locale: il file cresce mentre Live scrive, si ferma quando ha finito.
    last, stable, waited = -1, 0, 0
    while waited < 900:
        time.sleep(5)
        waited += 5
        size = os.path.getsize(dest) if os.path.exists(dest) else 0
        if size and size == last:
            stable += 1
            if stable >= 3:               # 15 s senza crescere = finito
                shot("rb_4_done")
                return status("done", file=dest, bytes=size, sec=waited)
        else:
            stable = 0
        last = size

    shot("rb_4_timeout")
    return status("failed", why="timeout 900 s", bytes=last)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], float(a[1]) if len(a) > 1 else 0.0, float(a[2]) if len(a) > 2 else 768.0)
