"""Controllo del processo Ableton Live e dei progetti, senza intervento umano.

Serve per iterare in autonomia: quando un plugin non espone qualcosa alla LOM
(es. il browser interno di KICK 3, che rilegge la cartella User solo all'avvio)
l'unica via e' chiudere e riaprire Live. Con questi comandi il ciclo
"genera preset -> riapri Live -> misura" si chiude senza chiedere niente.

Azioni: status | launch | quit | open_project | save | list_projects | find_exe
"""
from __future__ import annotations
import os
import re
import subprocess
import time
from pathlib import Path

from livemind.paths import PROJECT_DIRS

# Il titolo di Live e' "<set> - Ableton Live 12 Suite". Cercare la sola stringa
# "Ableton Live" pescava anche le finestre del browser con quel testo nel titolo.
WINDOW_RE = re.compile(r" - Ableton Live \d+", re.I)


def live_window():
    """Finestra principale di Live, escludendo browser e altre finestre che
    contengono 'Ableton Live' nel titolo."""
    import pygetwindow as gw
    for w in gw.getAllWindows():
        if WINDOW_RE.search(w.title):
            return w
    return None
DEFAULT_PROJECTS = Path(os.path.expanduser("~")) / "Documents" / "Ableton"


def find_exe() -> str | None:
    """Percorso dell'eseguibile di Live. Cerca prima il processo attivo (cosi'
    prende la versione davvero in uso), poi le install standard."""
    try:
        out = subprocess.run(
            ["wmic", "process", "where", "name like 'Ableton%'", "get", "ExecutablePath"],
            capture_output=True, text=True, timeout=15).stdout
        for line in out.splitlines():
            line = line.strip()
            if line.lower().endswith(".exe") and Path(line).exists():
                return line
    except Exception:
        pass
    for base in (r"C:\ProgramData\Ableton", r"C:\Program Files\Ableton"):
        p = Path(base)
        if not p.exists():
            continue
        cands = sorted(p.glob(r"*/Program/Ableton Live*.exe"), reverse=True)
        if cands:
            return str(cands[0])
    return None


def _pids() -> list[str]:
    # formato CSV: il nome immagine ("Ableton Live 12 Suite.exe") contiene spazi,
    # con l'output tabellare lo split prendeva la colonna sbagliata
    out = subprocess.run(["tasklist", "/fi", "imagename eq Ableton*", "/fo", "csv", "/nh"],
                         capture_output=True, text=True).stdout
    pids = []
    for line in out.splitlines():
        parts = [p.strip('" ') for p in line.split('","')]
        if len(parts) > 1 and parts[1].isdigit():
            pids.append(parts[1])
    return pids


def status() -> str:
    pids = _pids()
    return f"Live attivo (pid {', '.join(pids)})" if pids else "Live non in esecuzione"


def quit_live(force: bool = True, wait_s: float = 12.0) -> str:
    """Chiude Live. force=True usa taskkill /F: nessun dialogo di salvataggio,
    quindi le modifiche NON salvate si perdono — salvare prima con save()."""
    if not _pids():
        return "Live gia' chiuso"
    cmd = ["taskkill", "/IM", "Ableton Live*.exe", "/T"] + (["/F"] if force else [])
    subprocess.run(cmd, capture_output=True, text=True)
    deadline = time.time() + wait_s
    while time.time() < deadline:
        if not _pids():
            return "Live chiuso"
        time.sleep(0.5)
    return "Live non ha chiuso entro il timeout"


def launch(project: str | None = None, wait_s: float = 60.0) -> str:
    """Avvia Live, opzionalmente aprendo un progetto .als. Attende che il
    processo sia su (non che sia pronto: per quello si usa il ping LOM)."""
    exe = find_exe()
    if not exe:
        return "eseguibile di Live non trovato"
    args = [exe] + ([project] if project else [])
    subprocess.Popen(args, close_fds=True)
    deadline = time.time() + wait_s
    while time.time() < deadline:
        if _pids():
            return f"Live avviato ({Path(exe).name})" + (f" con {project}" if project else "")
        time.sleep(0.5)
    return "Live non risulta avviato entro il timeout"


def save() -> str:
    """Ctrl+S sulla finestra di Live. Se il set non e' mai stato salvato Live
    apre un dialogo: in quel caso serve un percorso, usare save_as a mano."""
    try:
        import pyautogui
    except ImportError:
        return "pyautogui/pygetwindow non installati"
    w = live_window()
    if w is None:
        return "finestra di Live non trovata"
    try:
        w.activate()
    except Exception:
        pass
    time.sleep(0.4)
    pyautogui.hotkey("ctrl", "s")
    time.sleep(1.0)
    return f"salvato: {w.title}"


def open_project(path: str, restart: bool = True) -> str:
    """Apre un .als. Con restart=True chiude Live prima: e' il modo per far
    rileggere ai plugin le cartelle preset aggiunte a runtime."""
    p = Path(path)
    if not p.exists():
        return f"progetto non trovato: {p}"
    msg = quit_live() + " | " if restart else ""
    return msg + launch(str(p))


# cartelle extra: variabile LIVEMIND_PROJECT_DIRS (vedi livemind/paths.py)
SEARCH_ROOTS = list(dict.fromkeys([DEFAULT_PROJECTS, *PROJECT_DIRS]))


def list_projects(root: str | None = None, limit: int = 40) -> str:
    """I set di Live non stanno per forza in Documents\\Ableton: se non si passa
    una cartella si cerca nelle posizioni piu' probabili."""
    roots = [Path(root)] if root else [p for p in SEARCH_ROOTS if p.exists()]
    found: dict[str, float] = {}
    for base in roots:
        if not base.exists():
            continue
        for f in base.rglob("*.als"):
            if "Backup" in f.parts:
                continue  # i backup automatici sporcherebbero la lista
            try:
                found[str(f)] = f.stat().st_mtime
            except OSError:
                pass
    if not found:
        return "nessun .als trovato in: " + ", ".join(str(r) for r in roots)
    ordered = sorted(found, key=lambda k: found[k], reverse=True)
    return "\n".join(ordered[:limit])


def dispatch(args: dict) -> str:
    a = args.get("action")
    if a == "status":
        return status()
    if a == "find_exe":
        return find_exe() or "non trovato"
    if a == "launch":
        return launch(args.get("project"))
    if a == "quit":
        return quit_live(force=bool(args.get("force", True)))
    if a == "open_project":
        return open_project(args["path"], restart=bool(args.get("restart", True)))
    if a == "save":
        return save()
    if a == "list_projects":
        return list_projects(args.get("root"), int(args.get("limit", 40)))
    return f"azione ableton sconosciuta: {a}"
