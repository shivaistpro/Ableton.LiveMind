"""Push-to-talk: tieni premuto F9, parla, rilascia → trascrizione locale → brain.

Zero CPU quando non premi. Nessun audio esce dal PC (faster-whisper locale).
"""
from __future__ import annotations
import threading

import numpy as np

try:
    import sounddevice as sd
    from pynput import keyboard
    _HAS_DEPS = True
except ImportError:  # pragma: no cover
    _HAS_DEPS = False

SR = 16000
BLOCK = int(SR * 0.03)  # 30 ms
MIN_SECONDS = 0.4
PTT_KEY = "f9"


class PushToTalkListener(threading.Thread):
    def __init__(self, on_command, model_size: str = "small", device=None):
        super().__init__(daemon=True)
        if not _HAS_DEPS:
            raise RuntimeError("pip install sounddevice pynput faster-whisper")
        self.on_command = on_command
        self.model_size = model_size
        self.device = device
        self.enabled = True
        self._pressed = threading.Event()
        self._stop = threading.Event()
        self._model = None

    def _load_model(self):
        from faster_whisper import WhisperModel
        print(f"[voce] carico whisper '{self.model_size}'...")
        self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        print(f"[voce] pronto — tieni premuto {PTT_KEY.upper()} e parla")

    def _on_press(self, key):
        if getattr(key, "name", None) == PTT_KEY:
            self._pressed.set()

    def _on_release(self, key):
        if getattr(key, "name", None) == PTT_KEY:
            self._pressed.clear()

    def _transcribe(self, audio: np.ndarray) -> str:
        segments, _ = self._model.transcribe(
            audio, language="it", beam_size=1, vad_filter=True)
        return " ".join(s.text for s in segments).strip()

    def run(self):
        try:
            self._load_model()
        except Exception as e:
            print(f"[voce] non disponibile: {e}")
            return
        kb = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        kb.start()
        while not self._stop.is_set():
            # attesa passiva: nessuno stream aperto finché non premi
            if not self._pressed.wait(timeout=0.2):
                continue
            if not self.enabled:
                self._pressed.clear()
                continue
            print("\n[voce] REC... (rilascia F9 per inviare)")
            chunks = []
            with sd.InputStream(samplerate=SR, channels=1, dtype="float32",
                                blocksize=BLOCK, device=self.device) as stream:
                while self._pressed.is_set() and not self._stop.is_set():
                    block, _ = stream.read(BLOCK)
                    chunks.append(block[:, 0].copy())
            if not chunks:
                continue
            audio = np.concatenate(chunks)
            if len(audio) < SR * MIN_SECONDS:
                print("[voce] troppo corto, riprova")
                continue
            try:
                text = self._transcribe(audio)
            except Exception as e:
                print(f"[voce] errore trascrizione: {e}")
                continue
            if not text:
                print("[voce] non ho capito, riprova")
                continue
            print(f"[voce] \"{text}\"")
            self.on_command(text)
        kb.stop()

    def stop(self):
        self._stop.set()
        self._pressed.set()  # sblocca il wait
