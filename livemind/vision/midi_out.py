"""Uscita MIDI virtuale verso Live (Windows: creare prima una porta con loopMIDI)."""
from __future__ import annotations

try:
    import mido
    _HAS_MIDO = True
except ImportError:  # pragma: no cover
    _HAS_MIDO = False


class MidiOut:
    def __init__(self, port_name: str = "LIVEMIND"):
        if not _HAS_MIDO:
            raise RuntimeError("pip install mido python-rtmidi")
        names = [n for n in mido.get_output_names() if port_name.lower() in n.lower()]
        if not names:
            raise RuntimeError(
                f"Porta MIDI '{port_name}' non trovata. Crea la porta in loopMIDI "
                f"e abilitala in Live (Preferences > MIDI > Track In).")
        self.port = mido.open_output(names[0])

    def note_on(self, pitch: int, velocity: int = 100, channel: int = 0):
        self.port.send(mido.Message("note_on", note=pitch, velocity=velocity, channel=channel))

    def note_off(self, pitch: int, channel: int = 0):
        self.port.send(mido.Message("note_off", note=pitch, channel=channel))

    def close(self):
        self.port.close()
