"""LIVEMIND — entry point con console gestionale (prompt_toolkit).

- riga di input fissa in basso, mai interrotta dai log
- stderr nativo (MediaPipe/TFLite) dirottato su livemind.log
- barra di stato: connessione Live, modalità vision, voce

Comandi: /mode macro|gesture|airmidi|off · /voice on|off · /log · /quit
"""
from __future__ import annotations
import argparse
import os
import sys
import threading

LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "livemind.log")


def _redirect_native_stderr(path: str):
    """Dirotta il fd 2 (stderr C/C++: clearcut, W0000, XNNPACK...) su file."""
    f = open(path, "a", buffering=1, encoding="utf-8", errors="replace")
    os.dup2(f.fileno(), 2)
    sys.stderr = f


from livemind.osc.client import AbletonOSCClient
from livemind.osc.live import LiveController
from livemind.lom_client import LomClient
from livemind.vision.modes import (Mode, MacroMode, MacroTarget,
                                   GestureMode, AirMidiMode)


class VisionLoop(threading.Thread):
    def __init__(self, live, midi=None, camera_index: int = 0, say=print):
        super().__init__(daemon=True)
        self.live = live
        self.midi = midi
        self.say = say
        self.mode: Mode | None = None
        self._stop = threading.Event()
        self.camera_index = camera_index
        self.macro = MacroMode(targets={
            "rx": MacroTarget(0, 0, 1), "ry": MacroTarget(0, 0, 2),
            "lx": MacroTarget(0, 0, 3), "ly": MacroTarget(0, 0, 4)})
        self.gesture = GestureMode()
        self.airmidi = AirMidiMode()

    def run(self):
        try:
            import cv2
            from livemind.vision.tracker import HandTracker
        except Exception as e:
            self.say(f"[vision] non disponibile: {e}")
            return
        tracker = None
        while not self._stop.is_set():
            if self.mode is None:
                # webcam OFF: rilascia camera e finestra, idle finche non si sceglie una modalita
                if tracker is not None:
                    tracker.close()
                    cv2.destroyAllWindows()
                    cv2.waitKey(1)
                    tracker = None
                    self.say("[vision] webcam spenta")
                self._stop.wait(0.1)
                continue
            if tracker is None:
                tracker = HandTracker(self.camera_index)
                self.say("[vision] webcam attiva")
            frame, hands = tracker.read()
            if frame is None:
                continue
            if self.mode == Mode.MACRO and hands:
                for tgt, v in self.macro.process(hands):
                    self.live.set_device_param(tgt.track, tgt.device, tgt.param, v)
            elif self.mode == Mode.GESTURE:
                lm = hands.get("right") or hands.get("left") or []
                act = self.gesture.process(lm)
                if act:
                    self._do(act)
            elif self.mode == Mode.AIRMIDI and self.midi:
                lm = hands.get("right") or hands.get("left") or []
                ev = self.airmidi.process(lm)
                if ev:
                    kind, pitch = ev
                    (self.midi.note_on if kind == "note_on" else self.midi.note_off)(pitch)
            label = self.mode.value if self.mode else "off"
            cv2.putText(frame, f"LIVEMIND [{label}]", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 128), 2)
            cv2.imshow("LIVEMIND vision", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                self.mode = None
        if tracker is not None:
            tracker.close()
        cv2.destroyAllWindows()

    def _do(self, act):
        a = act.action
        if a == "stop_all": self.live.stop_all_clips()
        elif a == "record_toggle": self.live.record(True)
        elif a == "fire_scene": self.live.fire_scene(act.arg)
        elif a == "tap_tempo": self.live.tap_tempo()
        self.say(f"[gesture] {a}({act.arg})")

    def stop(self):
        self._stop.set()


def main():
    ap = argparse.ArgumentParser(description="LIVEMIND — AI copilot per Ableton Live")
    ap.add_argument("--no-vision", action="store_true")
    ap.add_argument("--no-voice", action="store_true")
    ap.add_argument("--no-brain", action="store_true")
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--debug", action="store_true", help="stderr in console (no log file)")
    args = ap.parse_args()

    if not args.debug:
        _redirect_native_stderr(LOG_FILE)

    # console gestionale
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.patch_stdout import patch_stdout
        from prompt_toolkit.formatted_text import HTML
        _TUI = True
    except ImportError:
        _TUI = False
        print("[ui] prompt_toolkit non installato: console basica (pip install prompt_toolkit)")

    print("Connessione ad AbletonOSC...")
    client = AbletonOSCClient()
    live = LiveController(client)
    snap = live.snapshot()
    connected = snap["tempo"] is not None
    if connected:
        print(f"[live] connesso: {snap['num_tracks']} tracce, {snap['tempo']} BPM")
    else:
        print("[live] NON risponde: controlla AbletonOSC in Preferences > Link/MIDI")

    lom = LomClient()
    lom_ok = lom.ping().get("ok", False)
    print(f"[lom] {'connesso (Remote Script LiveMind attivo)' if lom_ok else 'NON raggiungibile: carica il Control Surface LiveMind in Preferences'}")

    midi = None
    try:
        from livemind.vision.midi_out import MidiOut
        midi = MidiOut()
        print("[midi] porta LIVEMIND ok")
    except Exception as e:
        print(f"[midi] non attivo: {e}")

    analyzer = None
    try:
        from livemind.audio.analyzer import MasterAnalyzer
        analyzer = MasterAnalyzer()
    except Exception as e:
        print(f"[audio] analyzer non attivo: {e}")

    loader = None
    try:
        from livemind.osc.loader import DeviceLoader
        loader = DeviceLoader()
        print("[loader] caricamento VST attivo")
    except Exception as e:
        print(f"[loader] non attivo: {e}")

    bridge = None
    try:
        from livemind.bridge import BridgeServer
        bridge_dir = os.path.join(os.path.dirname(LOG_FILE), "bridge")
        bridge = BridgeServer(bridge_dir, live, analyzer, loader, lom=lom)
        bridge.start()
    except Exception as e:
        print(f"[bridge] non attivo: {e}")

    vision = None
    if not args.no_vision:
        vision = VisionLoop(live, midi, args.camera)
        vision.start()

    agent = None
    agent_lock = threading.Lock()
    if not args.no_brain:
        try:
            from livemind.brain.agent import LiveMindAgent
            agent = LiveMindAgent(live, analyzer, loader, lom=lom)
            print("[brain] Claude attivo")
        except Exception as e:
            print(f"[brain] API non attiva ({e}) — uso il bridge: parla con il tuo agente IA via bridge")

    def run_agent(text: str):
        with agent_lock:
            reply = agent.chat(text, on_action=lambda n, i: print(f"  [live] {n} {i}"))
        print(f"livemind> {reply}")

    def voice_to_bridge(text: str):
        # modalita BRIDGE: nessun brain locale -> la trascrizione va nel bridge
        try:
            from livemind.bridge import write_voice_transcript
            bdir = os.path.join(os.path.dirname(LOG_FILE), "bridge")
            write_voice_transcript(bdir, text)
        except Exception as e:
            print(f"[voce] scrittura bridge fallita: {e}")
        print(f"[voce->bridge] {text}")

    voice = None
    if not args.no_voice:
        try:
            from livemind.voice.listener import PushToTalkListener
            voice = PushToTalkListener(run_agent if agent else voice_to_bridge)
            voice.start()
        except Exception as e:
            print(f"[voce] non attiva: {e}")

    def toolbar():
        parts = [
            f"Live: {'OK' if connected else 'OFF'}",
            f"LOM: {'OK' if lom_ok else 'OFF'}",
            f"vision: {vision.mode.value if (vision and vision.mode) else 'off'}",
            f"voce: {'F9' if (voice and voice.enabled) else 'off'}",
            "log: livemind.log",
        ]
        return HTML(" <b>LIVEMIND</b> | " + " | ".join(parts))

    def handle(line: str) -> bool:
        """Ritorna False per uscire."""
        if line == "/quit":
            return False
        if line == "/log":
            try:
                with open(LOG_FILE, encoding="utf-8", errors="replace") as f:
                    tail = f.readlines()[-15:]
                print("".join(tail) or "(log vuoto)")
            except FileNotFoundError:
                print("(nessun log)")
            return True
        if line.startswith("/voice"):
            arg = line.split()[-1] if len(line.split()) > 1 else "on"
            if voice:
                voice.enabled = (arg != "off")
                print(f"[voce] {'attiva (F9)' if voice.enabled else 'in pausa'}")
            else:
                print("[voce] non attiva")
            return True
        if line.startswith("/mode"):
            arg = line.split()[-1] if len(line.split()) > 1 else "off"
            if vision:
                try:
                    vision.mode = None if arg == "off" else Mode(arg)
                    print(f"[vision] modalità: {arg}")
                except ValueError:
                    print(f"[vision] modalità sconosciuta: {arg}")
            return True
        if agent:
            run_agent(line)
        else:
            print("(brain non attivo: imposta ANTHROPIC_API_KEY e riavvia)")
        return True

    print("Pronto. /mode · /voice · /log · /quit\n")
    if _TUI:
        session = PromptSession()
        with patch_stdout(raw=True):
            while True:
                try:
                    line = session.prompt(HTML("<ansigreen><b>tu></b></ansigreen> "),
                                          bottom_toolbar=toolbar).strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if line and not handle(line):
                    break
    else:
        while True:
            try:
                line = input("tu> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if line and not handle(line):
                break

    if vision:
        vision.stop()
    if voice:
        voice.stop()
    if bridge:
        bridge.stop()
    client.close()


if __name__ == "__main__":
    main()
