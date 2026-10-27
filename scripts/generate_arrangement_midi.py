"""Genera i .mid per il groove tribe/hardtekno 150 BPM da importare in
Arrangement View (drag&drop) — bypassa il disegno note a mano via GUI.

Struttura (32 bar, 4/4, 150 BPM):
  1-4   intro   : kick four-on-floor, perc leggera
  5-12  build   : + bass tribe (offbeat 16th), perc piena
  13-28 drop    : + acid lead (Operator, pattern con salti d'ottava)
  29-30 break   : kick out, bass sostenuta filtrata, solo perc
  31-32 outro   : fill di rientro, torna kick pieno

ponytail: pattern building block (four_on_floor/tribe_offbeat/acid_loop) invece
di note-by-note per ogni bar — piu' corto, stesso risultato musicale.
"""
from __future__ import annotations
import os
import mido

BPM = 150
TPB = 480  # ticks per beat
BAR = TPB * 4
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "out")

KICK_NOTE = 36
BASS_ROOT = 36
BASS_TURN = 43
PERC_HAT = 42
PERC_CLAP = 39
LEAD_ROOT = 48


def _track(notes):
    """notes: lista di (tick_on, dur_ticks, pitch, vel). Ritorna MidiTrack."""
    mid = mido.MidiFile(ticks_per_beat=TPB)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM), time=0))
    events = []
    for on, dur, pitch, vel in notes:
        events.append((on, 1, pitch, vel))       # note_on
        events.append((on + dur, 0, pitch, 0))    # note_off
    events.sort(key=lambda e: (e[0], e[1]))  # note_off prima di note_on a parita' tick
    last = 0
    for tick, kind, pitch, vel in events:
        delta = tick - last
        last = tick
        if kind == 1:
            tr.append(mido.Message("note_on", note=pitch, velocity=vel, time=delta))
        else:
            tr.append(mido.Message("note_off", note=pitch, velocity=0, time=delta))
    return mid


def kick_pattern(bar_from, bar_to, note=KICK_NOTE, vel=124):
    return [(b * BAR + beat * TPB, int(TPB * 0.35), note, vel)
            for b in range(bar_from, bar_to) for beat in range(4)]


def tribe_bass_pattern(bar_from, bar_to):
    offsets = [0.75, 1.75, 2.75, 3.75]
    out = []
    for i, b in enumerate(range(bar_from, bar_to)):
        for j, off in enumerate(offsets):
            pitch = BASS_TURN if (j == 3 and (i % 4 == 3)) else BASS_ROOT
            out.append((b * BAR + int(off * TPB), int(TPB * 0.4), pitch, 104))
    return out


def perc_pattern(bar_from, bar_to, full=True):
    out = []
    for b in range(bar_from, bar_to):
        for step in range(8):  # 8th notes
            tick = b * BAR + step * (TPB // 2)
            if step % 2 == 1 or full:
                vel = 90 if step % 4 != 2 else 70
                out.append((tick, int(TPB * 0.15), PERC_HAT, vel))
        out.append((b * BAR + 2 * TPB, int(TPB * 0.3), PERC_CLAP, 100))  # clap sul 3
    return out


def acid_lead_pattern(bar_from, bar_to):
    # semplice loop di 8 step che ricorda un acid bassline: root, ottava, quinta, root
    steps = [LEAD_ROOT, LEAD_ROOT, LEAD_ROOT + 12, LEAD_ROOT,
             LEAD_ROOT + 7, LEAD_ROOT, LEAD_ROOT + 3, LEAD_ROOT]
    out = []
    for b in range(bar_from, bar_to):
        for step, pitch in enumerate(steps):
            tick = b * BAR + step * (TPB // 2)
            vel = 110 if step == 0 else 90
            out.append((tick, int(TPB * 0.45), pitch, vel))
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    kick = (kick_pattern(0, 4, vel=110)
            + kick_pattern(4, 28, vel=124)
            + kick_pattern(30, 32, vel=124))  # kick out in break (28-30)
    bass = tribe_bass_pattern(4, 28) + tribe_bass_pattern(30, 32)
    perc = perc_pattern(0, 4, full=False) + perc_pattern(4, 32, full=True)
    lead = acid_lead_pattern(12, 28)

    _track(kick).save(os.path.join(OUT_DIR, "01_kick909.mid"))
    _track(bass).save(os.path.join(OUT_DIR, "02_tribebass.mid"))
    _track(perc).save(os.path.join(OUT_DIR, "03_perc.mid"))
    _track(lead).save(os.path.join(OUT_DIR, "04_acidlead.mid"))
    print("OK: 4 file .mid in", OUT_DIR)


if __name__ == "__main__":
    main()
