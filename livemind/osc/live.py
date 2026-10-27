"""LiveController: wrapper alto livello sulla Live Object Model via AbletonOSC.

Riferimento address space: https://github.com/ideoforms/AbletonOSC
Tutte le funzioni sono sottili e deterministiche: la logica sta nel brain.
"""
from __future__ import annotations
from typing import Any, Optional


class LiveController:
    def __init__(self, client):
        self.c = client

    # ---- Transport ----
    def play(self):            self.c.send("/live/song/start_playing")
    def stop(self):            self.c.send("/live/song/stop_playing")
    def record(self, on=True): self.c.send("/live/song/set/record_mode", int(on))
    def set_tempo(self, bpm: float): self.c.send("/live/song/set/tempo", float(bpm))
    def get_tempo(self) -> Optional[float]:
        r = self.c.query("/live/song/get/tempo")
        return float(r[0]) if r else None
    def metronome(self, on: bool): self.c.send("/live/song/set/metronome", int(on))
    def tap_tempo(self):       self.c.send("/live/song/tap_tempo")

    # ---- Scene / Clip ----
    def fire_scene(self, scene: int): self.c.send("/live/scene/fire", scene)
    def fire_clip(self, track: int, clip: int): self.c.send("/live/clip_slot/fire", track, clip)
    def stop_clip(self, track: int, clip: int): self.c.send("/live/clip_slot/stop", track, clip)
    def stop_all_clips(self): self.c.send("/live/song/stop_all_clips")
    def create_midi_track(self, index: int = -1): self.c.send("/live/song/create_midi_track", index)
    def create_audio_track(self, index: int = -1): self.c.send("/live/song/create_audio_track", index)
    def delete_track(self, index: int): self.c.send("/live/song/delete_track", int(index))
    def create_clip(self, track: int, clip: int, length_beats: float):
        self.c.send("/live/clip_slot/create_clip", track, clip, float(length_beats))
    def add_notes(self, track: int, clip: int, notes: list[dict]):
        """notes: [{pitch, start, duration, velocity, mute}]"""
        for n in notes:
            self.c.send("/live/clip/add/notes", track, clip,
                        int(n["pitch"]), float(n["start"]), float(n["duration"]),
                        int(n.get("velocity", 100)), int(n.get("mute", 0)))

    # ---- Mixer ----
    def set_volume(self, track: int, value: float):
        self.c.send("/live/track/set/volume", track, max(0.0, min(1.0, value)))
    def set_pan(self, track: int, value: float):
        self.c.send("/live/track/set/panning", track, max(-1.0, min(1.0, value)))
    def set_send(self, track: int, send: int, value: float):
        self.c.send("/live/track/set/send", track, send, max(0.0, min(1.0, value)))
    def mute(self, track: int, on: bool): self.c.send("/live/track/set/mute", track, int(on))
    def solo(self, track: int, on: bool): self.c.send("/live/track/set/solo", track, int(on))
    def arm(self, track: int, on: bool):  self.c.send("/live/track/set/arm", track, int(on))
    def get_track_names(self) -> list[str]:
        n = self.c.query("/live/song/get/num_tracks")
        if not n:
            return []
        names = []
        for i in range(int(n[0])):
            r = self.c.query("/live/track/get/name", i)
            names.append(str(r[1]) if r and len(r) > 1 else f"Track {i}")
        return names

    # ---- Arrangement / timeline ----
    def goto_time(self, beats: float): self.c.send("/live/song/set/current_song_time", float(beats))
    def get_time(self):
        r = self.c.query("/live/song/get/current_song_time")
        return float(r[0]) if r else None
    def jump_by(self, beats: float): self.c.send("/live/song/jump_by", float(beats))
    def set_loop(self, on: bool): self.c.send("/live/song/set/loop", int(on))
    def set_loop_region(self, start: float, length: float):
        self.c.send("/live/song/set/loop_start", float(start))
        self.c.send("/live/song/set/loop_length", float(length))
    def punch(self, punch_in: bool, punch_out: bool):
        self.c.send("/live/song/set/punch_in", int(punch_in))
        self.c.send("/live/song/set/punch_out", int(punch_out))
    def add_cue(self): self.c.send("/live/song/cue_point/add_or_delete")
    def jump_cue(self, forward: bool = True):
        self.c.send("/live/song/jump_to_next_cue" if forward else "/live/song/jump_to_prev_cue")
    def back_to_arranger(self): self.c.send("/live/song/set/back_to_arranger", 0)
    def arrangement_overdub(self, on: bool): self.c.send("/live/song/set/arrangement_overdub", int(on))

    # ---- Device / Macro ----
    def set_device_param(self, track: int, device: int, param: int, value: float):
        self.c.send("/live/device/set/parameter/value", track, device, param, float(value))
    def get_device_params(self, track: int, device: int) -> Optional[tuple]:
        return self.c.query("/live/device/get/parameters/name", track, device)
    def get_devices(self, track: int) -> Optional[tuple]:
        return self.c.query("/live/track/get/devices/name", track)

    def get_param_values(self, track: int, device: int):
        return self.c.query("/live/device/get/parameters/value", track, device)

    def select_track(self, track: int):
        self.c.send("/live/view/set/selected_track", track)

    # ---- Stato progetto (per il brain) ----
    def snapshot(self) -> dict[str, Any]:
        tempo = self.get_tempo()
        tracks = self.get_track_names()
        return {"tempo": tempo, "tracks": tracks, "num_tracks": len(tracks)}

    # ---- Layer OSC generico: copre l'intero address space AbletonOSC anche
    # dove non esiste (ancora) un metodo dedicato qui sopra. Riferimento:
    # https://github.com/ideoforms/AbletonOSC — address = "/live/{namespace}/{get|set|method}/{property}"
    def osc_get(self, address: str, *args: Any) -> Optional[tuple]:
        """GET grezzo: query un address OSC arbitrario e attende la risposta.
        Es: osc_get('/live/track/get/color', 0) -> (0, argb_color)"""
        return self.c.query(address, *args)

    def osc_set(self, address: str, *args: Any) -> None:
        """SET/CALL grezzo (fire-and-forget): imposta una proprieta' o invoca
        un metodo su un address OSC arbitrario.
        Es: osc_set('/live/clip/set/name', 0, 0, 'Acid Loop')"""
        self.c.send(address, *args)

    # ---- Track: proprieta' non coperte da mixer() ----
    def get_track_name(self, track: int) -> Optional[str]:
        r = self.c.query("/live/track/get/name", track)
        return str(r[1]) if r and len(r) > 1 else None
    def set_track_name(self, track: int, name: str): self.c.send("/live/track/set/name", track, name)
    def get_track_color(self, track: int) -> Optional[int]:
        r = self.c.query("/live/track/get/color", track)
        return int(r[1]) if r and len(r) > 1 else None
    def set_track_color(self, track: int, color: int): self.c.send("/live/track/set/color", track, int(color))
    def delete_device(self, track: int, device: int): self.c.send("/live/track/delete_device", track, device)
    def delete_clip(self, track: int, clip: int): self.c.send("/live/track/delete_clip", track, clip)

    # ---- Clip: proprieta' e metodi non coperti da write_notes/create_clip ----
    def fire_clip_direct(self, track: int, clip: int): self.c.send("/live/clip/fire", track, clip)
    def get_clip_property(self, track: int, clip: int, prop: str) -> Optional[tuple]:
        return self.c.query(f"/live/clip/get/{prop}", track, clip)
    def set_clip_property(self, track: int, clip: int, prop: str, value: Any):
        self.c.send(f"/live/clip/set/{prop}", track, clip, value)
    def get_clip_notes(self, track: int, clip: int) -> Optional[tuple]:
        return self.c.query("/live/clip/get/notes", track, clip)
    def remove_clip_notes(self, track: int, clip: int):
        self.c.send("/live/clip/remove/notes", track, clip)

    # ---- Clip Slot: creazione/duplicazione/verifica contenuto ----
    def clip_slot_has_clip(self, track: int, clip: int) -> Optional[bool]:
        r = self.c.query("/live/clip_slot/get/has_clip", track, clip)
        return bool(r[2]) if r and len(r) > 2 else None
    def clip_slot_create_clip(self, track: int, clip: int, length_beats: float):
        self.c.send("/live/clip_slot/create_clip", track, clip, float(length_beats))
    def clip_slot_delete_clip(self, track: int, clip: int):
        self.c.send("/live/clip_slot/delete_clip", track, clip)
    def clip_slot_duplicate_clip_to(self, src_track: int, src_clip: int, dst_track: int, dst_clip: int):
        self.c.send("/live/clip_slot/duplicate_clip_to", src_track, src_clip, dst_track, dst_clip)

    # ---- Device: lettura completa parametri (nome + valore + valore leggibile + range) ----
    def get_device_params_full(self, track: int, device: int) -> list[dict[str, Any]]:
        """Nome, valore normalizzato, valore leggibile (es. '2500 Hz'), min, max
        per ogni parametro automatabile del device. Fondamentale per validare
        i preset (es. verificare che 'Start Freq' di KICK 3 sia davvero ~260Hz
        e non solo 0.42 normalizzato)."""
        names = self.c.query("/live/device/get/parameters/name", track, device) or ()
        values = self.c.query("/live/device/get/parameters/value", track, device) or ()
        mins = self.c.query("/live/device/get/parameters/min", track, device) or ()
        maxs = self.c.query("/live/device/get/parameters/max", track, device) or ()
        # ogni risposta e' prefissata da (track, device); il payload utile parte da indice 2
        names, values, mins, maxs = names[2:], values[2:], mins[2:], maxs[2:]
        out = []
        for i, name in enumerate(names):
            value_str = None
            r = self.c.query("/live/device/get/parameter/value_string", track, device, i)
            if r and len(r) > 2:
                value_str = str(r[2])
            out.append({
                "index": i, "name": str(name),
                "value": values[i] if i < len(values) else None,
                "value_string": value_str,
                "min": mins[i] if i < len(mins) else None,
                "max": maxs[i] if i < len(maxs) else None,
            })
        return out

    # ---- Scene: nome/colore/tempo override ----
    def get_scene_property(self, scene: int, prop: str) -> Optional[tuple]:
        return self.c.query(f"/live/scene/get/{prop}", scene)
    def set_scene_property(self, scene: int, prop: str, value: Any):
        self.c.send(f"/live/scene/set/{prop}", scene, value)

    # ---- View: selezione UI corrente ----
    def get_selected_track(self) -> Optional[int]:
        r = self.c.query("/live/view/get/selected_track")
        return int(r[0]) if r else None
    def set_selected_track_view(self, track: int): self.c.send("/live/view/set/selected_track", track)
    def get_selected_scene(self) -> Optional[int]:
        r = self.c.query("/live/view/get/selected_scene")
        return int(r[0]) if r else None
    def set_selected_scene_view(self, scene: int): self.c.send("/live/view/set/selected_scene", scene)
    def get_selected_device(self) -> Optional[tuple]:
        return self.c.query("/live/view/get/selected_device")
    def set_selected_device_view(self, track: int, device: int):
        self.c.send("/live/view/set/selected_device", track, device)

    # ---- Song: extra (undo/redo, scene management, recording) ----
    def undo(self): self.c.send("/live/song/undo")
    def redo(self): self.c.send("/live/song/redo")
    def capture_midi(self): self.c.send("/live/song/capture_midi")
    def continue_playing(self): self.c.send("/live/song/continue_playing")
    def trigger_session_record(self): self.c.send("/live/song/trigger_session_record")
    def create_scene(self, index: int = -1): self.c.send("/live/song/create_scene", index)
    def delete_scene(self, index: int): self.c.send("/live/song/delete_scene", index)
    def duplicate_scene(self, index: int): self.c.send("/live/song/duplicate_scene", index)
    def get_num_scenes(self) -> Optional[int]:
        r = self.c.query("/live/song/get/num_scenes")
        return int(r[0]) if r else None

    # ---- Application: diagnostica ----
    def get_application_version(self) -> Optional[tuple]:
        return self.c.query("/live/application/get/version")
    def test_connection(self) -> Optional[tuple]:
        return self.c.query("/live/test")
