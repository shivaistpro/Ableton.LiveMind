"""Installa il Remote Script LiveMind nella User Library di Ableton di questo utente.

    python -m livemind.install            # copia/aggiorna remote_script/LiveMind
    python -m livemind.install --check    # dice solo cosa e' installato

Dopo la copia: in Live, Preferences > Link/Tempo/MIDI > Control Surface ->
"LiveMind" (se era gia' selezionato: metti "Nessuno" e poi di nuovo "LiveMind",
o riavvia Live, che tiene in cache i moduli Python).
AbletonOSC (canale OSC) si installa a mano: vedi docs/SETUP.md.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from livemind.paths import REMOTE_SCRIPTS, ROOT

SRC = ROOT / "remote_script" / "LiveMind"


def install(dest_root: Path = REMOTE_SCRIPTS) -> Path:
    if not SRC.is_dir():
        raise SystemExit(f"sorgente mancante: {SRC}")
    dest = dest_root / "LiveMind"
    dest.mkdir(parents=True, exist_ok=True)
    for f in SRC.glob("*.py"):  # solo i sorgenti: niente __pycache__ della repo
        shutil.copy2(f, dest / f.name)
    return dest


def check(dest_root: Path = REMOTE_SCRIPTS) -> str:
    rows = []
    for name in ("LiveMind", "AbletonOSC"):
        p = dest_root / name
        rows.append(f"{name:11} {'OK ' if p.is_dir() else 'MANCA'}  {p}")
    return "\n".join(rows)


if __name__ == "__main__":
    if "--check" not in sys.argv:
        print("installato in:", install())
    print(check())
