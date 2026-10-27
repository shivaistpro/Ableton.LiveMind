"""Percorsi di LIVEMIND, tutti sovrascrivibili da variabile d'ambiente.

Nessun path assoluto della macchina di sviluppo: i default sono relativi alla
repo o alle install standard dei plugin. Per adattarli alla propria macchina
impostare le variabili d'ambiente oppure copiare .env.example in .env:

    LIVEMIND_ROOT          radice della repo (default: rilevata da questo file)
    LIVEMIND_OUT           output di sessione: render, catture, screenshot (default: <root>/out)
    LIVEMIND_PROJECT_DIRS  cartelle dove cercare i set .als, separate da os.pathsep
    LIVEMIND_KICK3_PRESETS cartella User Presets di KICK 3
    LIVEMIND_OZONE_VST3    percorso del plugin Ozone 11 .vst3
    LIVEMIND_USER_LIBRARY  User Library di Ableton (se spostata, es. su OneDrive)
    LIVEMIND_MASTER_SRC    file audio sorgente per gli script di mastering offline
"""
from __future__ import annotations

import os
from pathlib import Path

HOME = Path.home()


def _load_dotenv(path: Path) -> None:
    """Carica KEY=VALUE da <repo>/.env senza sovrascrivere l'ambiente gia' impostato."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _env_path(name: str, default: Path) -> Path:
    v = os.environ.get(name)
    return Path(os.path.expandvars(os.path.expanduser(v))) if v else default


ROOT = _env_path("LIVEMIND_ROOT", Path(__file__).resolve().parents[1])
OUT = _env_path("LIVEMIND_OUT", ROOT / "out")
SHOTS = OUT / "shots"

ABLETON_USER_LIBRARY = _env_path("LIVEMIND_USER_LIBRARY", HOME / "Documents" / "Ableton" / "User Library")
REMOTE_SCRIPTS = ABLETON_USER_LIBRARY / "Remote Scripts"

_proj = os.environ.get("LIVEMIND_PROJECT_DIRS")
PROJECT_DIRS = ([Path(os.path.expanduser(p)) for p in _proj.split(os.pathsep) if p]
                if _proj else [HOME / "Documents" / "Ableton", HOME / "Documents", HOME / "Music"])

KICK3_PRESETS = _env_path("LIVEMIND_KICK3_PRESETS",
                          Path(r"C:\ProgramData\Sonic Academy\Kick 3\User\Presets"))
OZONE_VST3 = _env_path("LIVEMIND_OZONE_VST3",
                       Path(r"C:\Program Files\Common Files\VST3\iZotope\Ozone 11.vst3"))


def master_src() -> Path:
    """Sorgente per il mastering offline: obbligatoria, niente default personale."""
    v = os.environ.get("LIVEMIND_MASTER_SRC")
    if not v:
        raise SystemExit("imposta LIVEMIND_MASTER_SRC=<percorso del mix .wav da masterizzare>")
    return Path(os.path.expanduser(v))


def out_path(*parts: str) -> str:
    """Percorso dentro OUT (crea la cartella): out_path("shots", "x.png")."""
    p = OUT.joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p)
