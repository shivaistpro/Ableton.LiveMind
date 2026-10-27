"""TTS locale leggero — motore di sistema (SAPI5 su Windows) via pyttsx3,
nessun servizio cloud. Coda + thread dedicato: non blocca la UI Qt."""
from __future__ import annotations
import queue
import threading

try:
    import pyttsx3
    _HAS_TTS = True
except ImportError:  # pragma: no cover
    _HAS_TTS = False


class Speaker:
    def __init__(self):
        self.enabled = False
        self.available = _HAS_TTS
        self._q: "queue.Queue[str | None]" = queue.Queue()
        if _HAS_TTS:
            threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        engine = pyttsx3.init()
        while True:
            text = self._q.get()
            if text is None:
                break
            engine.say(text)
            engine.runAndWait()

    def speak(self, text: str) -> None:
        if self.enabled and self.available and text.strip():
            self._q.put(text)

    def stop(self) -> None:
        if self.available:
            self._q.put(None)
