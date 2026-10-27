"""Classificazione gesti da landmark MediaPipe (21 punti per mano).

Logica pura, indipendente da mediapipe: input = lista di (x, y) normalizzati.
Indici landmark: 0=polso, 4=pollice tip, 8=indice tip, 12=medio tip,
16=anulare tip, 20=mignolo tip. PIP: 6, 10, 14, 18. MCP pollice: 2.
"""
from __future__ import annotations
from enum import Enum

Point = tuple[float, float]

TIP_PIP = [(8, 6), (12, 10), (16, 14), (20, 18)]  # (tip, pip) per 4 dita


class Gesture(Enum):
    OPEN_PALM = "open_palm"
    FIST = "fist"
    POINT = "point"          # solo indice
    TWO = "two"              # indice + medio
    THUMB_UP = "thumb_up"
    UNKNOWN = "unknown"


def fingers_extended(lm: list[Point]) -> list[bool]:
    """4 dita (indice..mignolo): esteso se tip sopra il pip (y minore)."""
    return [lm[tip][1] < lm[pip][1] for tip, pip in TIP_PIP]


def thumb_extended(lm: list[Point]) -> bool:
    """Pollice: distanza orizzontale tip-mcp significativa rispetto alla mano."""
    hand_size = abs(lm[0][1] - lm[12][1]) or 1e-6
    return abs(lm[4][0] - lm[2][0]) > 0.35 * hand_size


def classify(lm: list[Point]) -> Gesture:
    if len(lm) < 21:
        return Gesture.UNKNOWN
    f = fingers_extended(lm)
    t = thumb_extended(lm)
    n = sum(f)
    if n == 4:
        return Gesture.OPEN_PALM
    if n == 0 and not t:
        return Gesture.FIST
    if n == 0 and t and lm[4][1] < lm[0][1]:
        return Gesture.THUMB_UP
    if f == [True, False, False, False]:
        return Gesture.POINT
    if f == [True, True, False, False]:
        return Gesture.TWO
    return Gesture.UNKNOWN


class GestureDebouncer:
    """Un gesto scatta solo se stabile per `hold_frames` frame consecutivi."""

    def __init__(self, hold_frames: int = 5):
        self.hold = hold_frames
        self._last = Gesture.UNKNOWN
        self._count = 0
        self._fired = Gesture.UNKNOWN

    def update(self, g: Gesture) -> Gesture | None:
        """Ritorna il gesto quando diventa stabile (una sola volta), altrimenti None."""
        if g == self._last:
            self._count += 1
        else:
            self._last, self._count = g, 1
        if self._count >= self.hold and g != self._fired and g != Gesture.UNKNOWN:
            self._fired = g
            return g
        if g == Gesture.UNKNOWN and self._count >= self.hold:
            self._fired = Gesture.UNKNOWN
        return None
