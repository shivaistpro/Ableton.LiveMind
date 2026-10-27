"""Guardie condivise per l'automazione UI di Live, da usare in OGNI script che
fa click/tasti alla cieca. Nate da un incidente: uno script di export lasciato
a meta' (dialogo Esporta ancora aperto) ha fatto si' che il prossimo script
cliccasse dentro quel dialogo invece che sull'arrangiamento, bloccandosi.

Due guardie:
- lock file: impedisce a due script di automazione di girare insieme e
  pestarsi i piedi (causa diretta dell'incidente).
- pulizia dialoghi orfani: prima di partire, chiude ogni finestra che non sia
  la finestra principale di Live ne' una nostra utility nota.
"""
from __future__ import annotations

import os, sys  # noqa: E401
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _paths import OUT, SHOTS, out_path  # noqa: E402,F401
import contextlib
import os
import time

import psutil  # gia' comune nell'ambiente Windows di produzione audio; se assente: pip install psutil
import pyautogui
import pygetwindow as gw

LOCK_PATH = out_path("ui_automation.lock")
KNOWN_HARMLESS = ("claude", "esplora file", "loopmidi", "program manager",
                  "impostazioni", "esperienza input di windows",
                  "ashotplugctrl", "ashdrcontrol", "nvidia geforce overlay",
                  "livemind bridge")


class UIBusyError(Exception):
    pass


@contextlib.contextmanager
def exclusive(name: str, max_age_s: float = 180.0):
    """Un solo script di automazione UI alla volta. Se un lock precedente e'
    piu' vecchio di max_age_s lo considera abbandonato (processo morto senza
    ripulire) e lo rilancia comunque, loggando l'anomalia."""
    if os.path.exists(LOCK_PATH):
        age = time.time() - os.path.getmtime(LOCK_PATH)
        if age < max_age_s:
            with open(LOCK_PATH, encoding="utf-8") as f:
                holder = f.read().strip()
            raise UIBusyError(
                "automazione UI gia' in corso (%s, da %.0fs) - aspetta o pulisci %s"
                % (holder, age, LOCK_PATH))
    with open(LOCK_PATH, "w", encoding="utf-8") as f:
        f.write("%s pid=%d t=%s" % (name, os.getpid(), time.strftime("%H:%M:%S")))
    try:
        yield
    finally:
        try:
            os.remove(LOCK_PATH)
        except OSError:
            pass


def close_stray_dialogs(max_rounds: int = 4) -> list[str]:
    """Chiude ogni finestra con titolo non vuoto che non sia Live ne' una
    finestra nota e innocua (Esplora file, Claude, ecc.). Un dialogo Esporta
    o Salva-con-nome lasciato aperto finisce qui. Ritorna i titoli chiusi."""
    closed = []
    for _ in range(max_rounds):
        stray = None
        for w in gw.getAllWindows():
            title = (w.title or "").strip()
            if not title:
                continue
            low = title.lower()
            if "ableton live" in low or any(k in low for k in KNOWN_HARMLESS):
                continue
            stray = w
            break
        if stray is None:
            break
        try:
            stray.activate()
        except Exception:
            pass
        time.sleep(0.4)
        pyautogui.press("escape")
        time.sleep(0.6)
        closed.append(stray.title)
    return closed


def focus_live():
    """minimize->restore->activate: activate() da solo non basta quando il
    chiamante e' un processo in background (anti focus-steal di Windows)."""
    w = None
    for cand in gw.getAllWindows():
        if "ableton live" in (cand.title or "").lower():
            w = cand
            break
    if w is None:
        return None
    if w.isMinimized:
        w.restore()
    time.sleep(0.4)
    w.minimize()
    time.sleep(0.3)
    w.restore()
    time.sleep(0.5)
    w.activate()
    time.sleep(0.8)
    active = gw.getActiveWindow()
    if not active or "ableton live" not in (active.title or "").lower():
        return None
    return w


def kill_stale_python(script_name: str, keep_pid: int | None = None):
    """Termina processi python.exe che stanno eseguendo script_name, tranne
    keep_pid (il processo corrente). Da usare quando un vecchio script di
    automazione e' rimasto appeso e ne blocca uno nuovo."""
    killed = []
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if keep_pid is not None and p.info["pid"] == keep_pid:
                continue
            cmdline = " ".join(p.info.get("cmdline") or [])
            if "python" in (p.info.get("name") or "").lower() and script_name in cmdline:
                p.kill()
                killed.append(p.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return killed
