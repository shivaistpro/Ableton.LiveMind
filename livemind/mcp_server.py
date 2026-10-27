"""Server MCP sincrono per Ableton Live — alternativa RPC diretta al bridge a file.

Espone via protocollo MCP (stdio) gli stessi comandi del bridge (livemind.bridge),
ma senza polling su inbox.jsonl: ogni chiamata tool arriva via stdio e si traduce
subito in una chiamata OSC verso Ableton. Riusa LiveController e dispatch() gia'
testati in livemind.brain.tools — nessuna logica duplicata.

Uso (registrato come server MCP esterno, es. Claude Desktop/Code, Codex CLI; ChatGPT con --http, vedi docs/SETUP.md):
  command: python
  args: ["-m", "livemind.mcp_server"]
  cwd: <LIVEMIND_DIR>

Requisiti runtime: Ableton Live 12 con AbletonOSC attivo (porte 11000/11001).
Se Live non risponde all'avvio, il server parte comunque: ogni tool call
ritorna un errore leggibile invece di far crashare il processo (vedi
dispatch() in brain/tools.py, che intrappola le eccezioni per tool).
"""
from __future__ import annotations
from typing import Any, Literal, Optional

from livemind.brain.tools import dispatch
from livemind.osc.client import AbletonOSCClient
from livemind.osc.live import LiveController


def build_tools(live, analyzer=None, loader=None) -> dict[str, Any]:
    """Ritorna {nome_tool: funzione pura}, senza toccare MCP. Testabile in isolamento
    con un FakeLive iniettato al posto della connessione OSC reale (vedi test_tools.py)."""

    def transport(
        action: Literal["play", "stop", "record_on", "record_off",
                         "metronome_on", "metronome_off", "set_tempo"],
        bpm: Optional[float] = None,
    ) -> str:
        """Controlla il transport: play, stop, record on/off, metronomo, tempo BPM."""
        args = {"action": action}
        if bpm is not None:
            args["bpm"] = bpm
        return dispatch("transport", args, live, analyzer, loader)

    def fire(
        what: Literal["scene", "clip", "stop_clip", "stop_all"],
        track: Optional[int] = None,
        index: Optional[int] = None,
    ) -> str:
        """Lancia o ferma scene e clip nella Session View."""
        args = {"what": what}
        if track is not None:
            args["track"] = track
        if index is not None:
            args["index"] = index
        return dispatch("fire", args, live, analyzer, loader)

    def mixer(
        track: int,
        param: Literal["volume", "pan", "send", "mute", "solo", "arm"],
        value: float,
        send_index: Optional[int] = None,
    ) -> str:
        """Mixer: volume (0-1), pan (-1..1), send (0-1), mute/solo/arm per traccia."""
        args = {"track": track, "param": param, "value": value}
        if send_index is not None:
            args["send_index"] = send_index
        return dispatch("mixer", args, live, analyzer, loader)

    def device_param(track: int, device: int, param: int, value: float) -> str:
        """Imposta un parametro (0-1 normalizzato) di un device su una traccia,
        incluse le macro dei rack (param 1-8 nei rack)."""
        args = {"track": track, "device": device, "param": param, "value": value}
        return dispatch("device_param", args, live, analyzer, loader)

    def set_param_by_name(track: int, device: int, param_name: str, value: float) -> str:
        """Imposta un parametro di un device/VST cercandolo per NOME (fuzzy match).
        Usa get_state(what='device_params') prima per vedere i nomi esatti esposti
        da AbletonOSC. value normalizzato 0-1."""
        args = {"track": track, "device": device, "param_name": param_name, "value": value}
        return dispatch("set_param_by_name", args, live, analyzer, loader)

    def create(
        what: Literal["midi_track", "audio_track", "midi_clip"],
        track: Optional[int] = None,
        clip: Optional[int] = None,
        length_beats: Optional[float] = None,
    ) -> str:
        """Crea tracce MIDI/audio o clip MIDI (length in beats)."""
        args = {"what": what}
        if track is not None:
            args["track"] = track
        if clip is not None:
            args["clip"] = clip
        if length_beats is not None:
            args["length_beats"] = length_beats
        return dispatch("create", args, live, analyzer, loader)

    def delete_track(
        track: Optional[int] = None,
        tracks: Optional[list[int]] = None,
    ) -> str:
        """Elimina una o piu tracce per indice (0-based). Operazione distruttiva:
        conferma con l'utente prima di usarlo su indici incerti."""
        args: dict[str, Any] = {}
        if track is not None:
            args["track"] = track
        if tracks is not None:
            args["tracks"] = tracks
        return dispatch("delete_track", args, live, analyzer, loader)

    def write_notes(track: int, clip: int, notes: list[dict[str, Any]]) -> str:
        """Scrive note MIDI in una clip: lista di {pitch, start, duration, velocity}.
        start/duration in beats."""
        args = {"track": track, "clip": clip, "notes": notes}
        return dispatch("write_notes", args, live, analyzer, loader)

    def get_state(
        what: Literal["snapshot", "devices", "device_params"],
        track: Optional[int] = None,
        device: Optional[int] = None,
    ) -> str:
        """Legge lo stato del progetto: tempo, tracce, device di una traccia,
        parametri (nome+valore) di un device."""
        args = {"what": what}
        if track is not None:
            args["track"] = track
        if device is not None:
            args["device"] = device
        return dispatch("get_state", args, live, analyzer, loader)

    def load_device(track: int, device_name: str) -> str:
        """Carica un device o VST dal browser di Live sulla traccia indicata
        (es. 'KICK 3', 'Acid V', 'Serum'). Automatizza la UI di Live (deve essere
        visibile): carica il PRIMO risultato della ricerca. Verifica con
        get_state(what='devices')."""
        args = {"track": track, "device_name": device_name}
        return dispatch("load_device", args, live, analyzer, loader)

    def arrangement(
        action: Literal["goto", "jump_by", "get_position", "loop_on", "loop_off",
                         "set_loop_region", "punch", "add_cue_here", "next_cue",
                         "prev_cue", "back_to_arrangement", "overdub_on",
                         "overdub_off", "record_start", "record_stop"],
        beats: Optional[float] = None,
        start: Optional[float] = None,
        length: Optional[float] = None,
        punch_in: Optional[bool] = None,
        punch_out: Optional[bool] = None,
    ) -> str:
        """Vista Arrangement: playhead, loop region, punch in/out, cue points,
        registrazione in arrangement, overdub."""
        args: dict[str, Any] = {"action": action}
        if beats is not None:
            args["beats"] = beats
        if start is not None:
            args["start"] = start
        if length is not None:
            args["length"] = length
        if punch_in is not None:
            args["punch_in"] = punch_in
        if punch_out is not None:
            args["punch_out"] = punch_out
        return dispatch("arrangement", args, live, analyzer, loader)

    def analyze_audio(seconds: float = 8) -> str:
        """Misura il master in tempo reale: LUFS integrato/short-term, true peak
        dBTP, bilanciamento spettrale. Richiede loopback audio configurato."""
        return dispatch("analyze_audio", {"seconds": seconds}, live, analyzer, loader)

    def osc_get(address: str, args: Optional[list[Any]] = None) -> str:
        """GET grezzo su un address OSC AbletonOSC arbitrario — copre l'intero
        address space (song/track/clip/device/clip_slot/scene/view/application),
        anche cio' che non ha ancora una convenience dedicata qui sotto.
        Es: address='/live/track/get/color', args=[0]."""
        return dispatch("osc_get", {"address": address, "args": args or []}, live, analyzer, loader)

    def osc_set(address: str, args: Optional[list[Any]] = None) -> str:
        """SET o CALL grezzo (fire-and-forget) su un address OSC arbitrario.
        Es: address='/live/clip/fire', args=[0, 2]."""
        return dispatch("osc_set", {"address": address, "args": args or []}, live, analyzer, loader)

    def track_meta(
        action: Literal["get_name", "set_name", "get_color", "set_color"],
        track: int,
        name: Optional[str] = None,
        color: Optional[int] = None,
    ) -> str:
        """Nome e colore di una traccia (non coperti da mixer)."""
        args: dict[str, Any] = {"action": action, "track": track}
        if name is not None:
            args["name"] = name
        if color is not None:
            args["color"] = color
        return dispatch("track_meta", args, live, analyzer, loader)

    def clip_property(
        action: Literal["get", "set"],
        track: int,
        clip: int,
        prop: str,
        value: Optional[Any] = None,
    ) -> str:
        """Get/set di una proprieta' clip qualsiasi: name, color, color_index,
        loop_start, loop_end, looping, gain, pitch_coarse, pitch_fine, warping,
        warp_mode, muted, start_marker, end_marker, launch_mode,
        launch_quantization, legato..."""
        args: dict[str, Any] = {"action": action, "track": track, "clip": clip, "prop": prop}
        if value is not None:
            args["value"] = value
        return dispatch("clip_property", args, live, analyzer, loader)

    def clip_notes_bulk(action: Literal["get", "remove"], track: int, clip: int) -> str:
        """Legge o rimuove TUTTE le note MIDI di una clip in blocco (per
        aggiungere note usa write_notes)."""
        return dispatch("clip_notes_bulk", {"action": action, "track": track, "clip": clip},
                         live, analyzer, loader)

    def clip_slot(
        action: Literal["has_clip", "create_clip", "delete_clip", "duplicate_clip_to", "fire", "stop"],
        track: int,
        clip: int,
        length_beats: Optional[float] = None,
        dst_track: Optional[int] = None,
        dst_clip: Optional[int] = None,
    ) -> str:
        """Gestione clip slot: presenza clip, creazione/cancellazione,
        duplicazione tra slot — per costruire pattern senza registrare a mano."""
        args: dict[str, Any] = {"action": action, "track": track, "clip": clip}
        if length_beats is not None:
            args["length_beats"] = length_beats
        if dst_track is not None:
            args["dst_track"] = dst_track
        if dst_clip is not None:
            args["dst_clip"] = dst_clip
        return dispatch("clip_slot", args, live, analyzer, loader)

    def device_params_full(track: int, device: int) -> str:
        """Elenco COMPLETO dei parametri di un device: nome, valore normalizzato
        0-1, valore leggibile in unita' reali (es. '2500 Hz', '-6.0 dB'), min, max.
        Usalo per VERIFICARE un preset dopo averlo applicato con device_param
        o set_param_by_name, non solo per leggerlo — cruciale con synth come
        KICK 3 dove 0.42 normalizzato non dice nulla senza il range reale."""
        return dispatch("device_params_full", {"track": track, "device": device}, live, analyzer, loader)

    def scene_property(action: Literal["get", "set"], scene: int, prop: str, value: Optional[Any] = None) -> str:
        """Get/set proprieta' di una scena: name, color, color_index, tempo,
        tempo_enabled, time_signature_numerator/denominator, time_signature_enabled."""
        args: dict[str, Any] = {"action": action, "scene": scene, "prop": prop}
        if value is not None:
            args["value"] = value
        return dispatch("scene_property", args, live, analyzer, loader)

    def view(
        action: Literal["get_selected_track", "set_selected_track", "get_selected_scene",
                         "set_selected_scene", "get_selected_device", "set_selected_device"],
        track: Optional[int] = None,
        scene: Optional[int] = None,
        device: Optional[int] = None,
    ) -> str:
        """Selezione UI corrente in Live: traccia, scena, device selezionati."""
        args: dict[str, Any] = {"action": action}
        if track is not None:
            args["track"] = track
        if scene is not None:
            args["scene"] = scene
        if device is not None:
            args["device"] = device
        return dispatch("view", args, live, analyzer, loader)

    def song_action(
        action: Literal["undo", "redo", "capture_midi", "continue_playing",
                         "trigger_session_record", "create_scene", "delete_scene",
                         "duplicate_scene", "get_num_scenes"],
        index: Optional[int] = None,
    ) -> str:
        """Azioni a livello song non coperte da transport/arrangement: undo,
        redo, capture_midi (cattura da session ad arrangement), continue_playing,
        trigger_session_record, create/delete/duplicate_scene, get_num_scenes."""
        args: dict[str, Any] = {"action": action}
        if index is not None:
            args["index"] = index
        return dispatch("song_action", args, live, analyzer, loader)

    def app_info(what: Literal["version", "test"]) -> str:
        """Diagnostica applicazione: versione Live e test di connettivita' di base."""
        return dispatch("app_info", {"what": what}, live, analyzer, loader)

    def connection_status() -> str:
        """Verifica subito se Ableton risponde via OSC (tempo + numero tracce).
        Usalo come primo comando ad ogni sessione, prima di qualsiasi altra azione:
        AbletonOSC puo' non essere attivo anche se Live e' aperto."""
        try:
            snap = live.snapshot()
        except Exception as e:  # connessione mai riuscita ad instaurarsi
            return f"ERRORE: impossibile interrogare AbletonOSC: {e}"
        if snap.get("tempo") is None:
            return ("Live NON risponde. Controlla: AbletonOSC installato come Remote "
                    "Script, Preferences > Link/MIDI/Sync > Control Surface = AbletonOSC, "
                    "porte 11000/11001 libere.")
        return f"connesso: {snap['num_tracks']} tracce, {snap['tempo']} BPM"

    return {
        "transport": transport,
        "fire": fire,
        "mixer": mixer,
        "device_param": device_param,
        "set_param_by_name": set_param_by_name,
        "create": create,
        "delete_track": delete_track,
        "write_notes": write_notes,
        "get_state": get_state,
        "load_device": load_device,
        "arrangement": arrangement,
        "analyze_audio": analyze_audio,
        "connection_status": connection_status,
        "osc_get": osc_get,
        "osc_set": osc_set,
        "track_meta": track_meta,
        "clip_property": clip_property,
        "clip_notes_bulk": clip_notes_bulk,
        "clip_slot": clip_slot,
        "device_params_full": device_params_full,
        "scene_property": scene_property,
        "view": view,
        "song_action": song_action,
        "app_info": app_info,
    }


def create_server(live, analyzer=None, loader=None):
    """Costruisce il FastMCP server registrando i tool. Import di 'mcp' qui dentro
    (non in cima al file) cosi' i test possono importare build_tools() senza avere
    il pacchetto 'mcp' installato."""
    from mcp.server.fastmcp import FastMCP

    server = FastMCP(
        "livemind-ableton",
        instructions=(
            "Controllo diretto e sincrono di Ableton Live via AbletonOSC "
            "(https://github.com/ideoforms/AbletonOSC). Chiama sempre connection_status "
            "per primo. device_param/set_param_by_name agiscono sui parametri automatabili "
            "reali del plugin caricato su una traccia (VST inclusi, es. KICK 3): usa "
            "device_params_full per vedere nomi, valori leggibili (Hz/dB/ms) e range prima "
            "di scrivere, e per VERIFICARE dopo aver scritto. Per operazioni non coperte da "
            "un tool dedicato (track_meta, clip_property, clip_slot, scene_property, view, "
            "song_action, app_info...), usa osc_get/osc_set con l'address OSC grezzo: "
            "copre l'intero address space Song/Track/Clip/Device/ClipSlot/Scene/View/Application. "
            "Nota: i listener OSC (start_listen/stop_listen) non sono esposti qui perche' "
            "richiedono un canale asincrono persistente, incompatibile con MCP request/response."
        ),
    )
    for name, func in build_tools(live, analyzer, loader).items():
        server.tool(name=name)(func)
    return server


def main() -> None:
    print("[livemind-mcp] connessione ad AbletonOSC...")
    client = AbletonOSCClient()
    live = LiveController(client)

    analyzer = None
    try:
        from livemind.audio.analyzer import MasterAnalyzer
        analyzer = MasterAnalyzer()
    except Exception as e:
        print(f"[livemind-mcp] analyzer non attivo: {e}")

    loader = None
    try:
        from livemind.osc.loader import DeviceLoader
        loader = DeviceLoader()
    except Exception as e:
        print(f"[livemind-mcp] loader (caricamento VST via UI) non attivo: {e}")

    server = create_server(live, analyzer, loader)
    print("[livemind-mcp] server pronto")
    from livemind.mcp_transport import run
    run(server)


if __name__ == "__main__":
    main()
