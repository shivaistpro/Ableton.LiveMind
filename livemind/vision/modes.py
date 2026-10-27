"""Le 3 modalità webcam. Logica pura e testabile: input landmark → azioni.

- MACRO:   posizione mani → valori continui (macro rack / mixer) via OSC
- GESTURE: gesti riconosciuti → azioni discrete (scene, mute, record...)
- AIRMIDI: griglia virtuale → note MIDI
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

from .gestures import Gesture, GestureDebouncer, classify, Point


class Mode(Enum):
    MACRO = "macro"
    GESTURE = "gesture"
    AIRMIDI = "airmidi"


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def smooth(prev: float, new: float, alpha: float = 0.35) -> float:
    """EMA one-pole: niente zipper sui parametri continui."""
    return prev + alpha * (new - prev)


@dataclass
class MacroTarget:
    track: int
    device: int
    param: int


@dataclass
class MacroMode:
    """Mano dx: X→macro A, Y→macro B. Mano sx: X→macro C, Y→macro D."""
    targets: dict[str, MacroTarget]  # chiavi: rx, ry, lx, ly
    _state: dict[str, float] = field(default_factory=dict)

    def process(self, hands: dict[str, list[Point]]) -> list[tuple[MacroTarget, float]]:
        out = []
        for hand_key, lm in hands.items():  # "right" / "left"
            if not lm:
                continue
            cx = _clamp01(sum(p[0] for p in lm) / len(lm))
            cy = _clamp01(1.0 - sum(p[1] for p in lm) / len(lm))  # su = più valore
            for axis, val in (("x", cx), ("y", cy)):
                key = ("r" if hand_key == "right" else "l") + axis
                tgt = self.targets.get(key)
                if tgt is None:
                    continue
                prev = self._state.get(key, val)
                v = smooth(prev, val)
                self._state[key] = v
                out.append((tgt, round(v, 4)))
        return out


@dataclass
class GestureAction:
    action: str            # es. "fire_scene", "stop_all", "record_toggle", "mute_toggle"
    arg: int = 0


DEFAULT_GESTURE_MAP: dict[Gesture, GestureAction] = {
    Gesture.OPEN_PALM: GestureAction("stop_all"),
    Gesture.FIST: GestureAction("record_toggle"),
    Gesture.POINT: GestureAction("fire_scene", 0),
    Gesture.TWO: GestureAction("fire_scene", 1),
    Gesture.THUMB_UP: GestureAction("tap_tempo"),
}


class GestureMode:
    def __init__(self, mapping: dict[Gesture, GestureAction] | None = None,
                 hold_frames: int = 5):
        self.map = mapping or dict(DEFAULT_GESTURE_MAP)
        self.debouncer = GestureDebouncer(hold_frames)

    def process(self, lm: list[Point]) -> GestureAction | None:
        fired = self.debouncer.update(classify(lm))
        return self.map.get(fired) if fired else None


@dataclass
class AirMidiMode:
    """Griglia cols x rows nel campo visivo → note. Trigger sul gesto POINT."""
    cols: int = 4
    rows: int = 2
    base_note: int = 36  # C1, comodo per drum rack
    _active: int | None = None

    def cell_to_note(self, col: int, row: int) -> int:
        return self.base_note + row * self.cols + col

    def process(self, lm: list[Point]) -> tuple[str, int] | None:
        """Ritorna ("note_on", pitch) al primo ingresso in una cella col dito indice,
        ("note_off", pitch) quando il dito esce o la mano sparisce."""
        if not lm or len(lm) < 9:
            if self._active is not None:
                off, self._active = self._active, None
                return ("note_off", off)
            return None
        x, y = lm[8]  # punta dell'indice
        col = min(self.cols - 1, max(0, int(x * self.cols)))
        row = min(self.rows - 1, max(0, int(y * self.rows)))
        note = self.cell_to_note(col, row)
        if classify(lm) != Gesture.POINT:
            if self._active is not None:
                off, self._active = self._active, None
                return ("note_off", off)
            return None
        if note != self._active:
            prev = self._active
            self._active = note
            return ("note_on", note) if prev is None else ("note_on", note)
        return None
