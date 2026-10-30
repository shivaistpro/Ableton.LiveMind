"""Caricamento di sample audio (wav/aif/flac...) in Live via LOM
(Live 12: ClipSlot.create_audio_clip(path) / Track.create_audio_clip(path, pos)).

Session: track + clip -> clip audio nello slot.
Arrangement: track + position (beats) -> clip audio sulla timeline.
Il path deve essere ASSOLUTO sulla macchina dove gira Live.
"""
from __future__ import annotations
import os


def load(lom, path: str, track: int, clip: int | None = None,
         position: float | None = None, name: str | None = None) -> str:
    if lom is None:
        return "canale LOM non disponibile (Remote Script LiveMind non raggiunge 127.0.0.1:9005)"
    if not os.path.isabs(path) or not os.path.isfile(path):
        return f"file non trovato (serve path assoluto): {path}"
    t = f"tracks:{int(track)}"
    if clip is not None:
        slot = [t, f"clip_slots:{int(clip)}"]
        r = lom.call(slot, "create_audio_clip", [path])
        if r.get("ok") and name:
            lom.set(slot + ["clip"], "name", name)
        where = f"session [{track},{clip}]"
    else:
        r = lom.call([t], "create_audio_clip", [path, float(position or 0.0)])
        where = f"arrangement traccia {track} @ {position or 0.0} beats"
    if not r.get("ok"):
        return f"ERRORE create_audio_clip: {r.get('error')} (serve una traccia AUDIO e Live 12)"
    return f"sample caricato in {where}: {os.path.basename(path)}"
