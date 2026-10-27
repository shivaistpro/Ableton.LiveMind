"""Segmentatore di parlato a energia: macchina a stati pura e testabile.

feed(rms, block) → None finché l'utterance non è completa, poi la lista dei
blocchi audio (parlato + coda). Soglia calibrata sull'ambiente dal chiamante.
"""
from __future__ import annotations


class UtteranceSegmenter:
    def __init__(self, threshold: float, silence_blocks: int = 27,
                 min_speech_blocks: int = 8, max_blocks: int = 500):
        self.threshold = threshold
        self.silence_blocks = silence_blocks
        self.min_speech = min_speech_blocks
        self.max_blocks = max_blocks
        self._buf: list = []
        self._speech = 0
        self._silence = 0
        self._active = False

    def _reset(self):
        self._buf, self._speech, self._silence, self._active = [], 0, 0, False

    def feed(self, rms: float, block) -> list | None:
        voiced = rms > self.threshold
        if not self._active:
            if voiced:
                self._active = True
                self._buf = [block]
                self._speech, self._silence = 1, 0
            return None
        self._buf.append(block)
        if voiced:
            self._speech += 1
            self._silence = 0
        else:
            self._silence += 1
        done = self._silence >= self.silence_blocks or len(self._buf) >= self.max_blocks
        if not done:
            return None
        out, ok = self._buf, self._speech >= self.min_speech
        self._reset()
        return out if ok else None
