"""KICK 3 .preset = XML <Kick3><PARAMS><PARAM id=.. value=../></PARAMS><DATA .../>.
~1006 PARAM editabili. Partire dai preset di fabbrica."""
from __future__ import annotations
import re


def get_param(xml: str, pid: str, default=None):
    m = re.search(r'<PARAM id="%s" value="([^"]*)"' % re.escape(pid), xml)
    return m.group(1) if m else default


def set_param(xml: str, pid: str, value) -> str:
    return re.sub(r'(<PARAM id="%s" value=")[^"]*(")' % re.escape(pid),
                  lambda m: m.group(1) + str(value) + m.group(2), xml, count=1)


def active_slots(xml: str):
    """indici slot con Type != 0 (layer attivi). Gli slot in KICK 3 sono 1..5."""
    out = []
    for s in range(1, 6):
        v = get_param(xml, f"Slot{s}Type", "0")
        try:
            if float(v) != 0.0:
                out.append(s)
        except ValueError:
            pass
    return out


def clear_sample(xml: str, slot: int) -> str:
    """svuota il campione incorporato di uno slot nel blob <DATA>."""
    return re.sub(r'(slot%d_File=")[^"]*(")' % slot, r"\g<1>////////\g<2>", xml, count=1)


def transpose_semi(xml: str, semitones: float) -> str:
    """somma semitoni al PitchSemi di tutti gli slot attivi (accordatura)."""
    for s in active_slots(xml):
        cur = float(get_param(xml, f"Slot{s}PitchSemi", "0") or 0)
        xml = set_param(xml, f"Slot{s}PitchSemi", round(cur + semitones, 4))
    return xml
