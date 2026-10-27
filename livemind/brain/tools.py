"""Tool schema (formato Anthropic tool-use) + dispatcher verso LiveController."""
from __future__ import annotations
from typing import Any

TOOLS: list[dict] = [
    {"name": "transport", "description": "Controlla il transport di Live: play, stop, record on/off, metronomo, tempo BPM.",
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["play", "stop", "record_on", "record_off", "metronome_on", "metronome_off", "set_tempo"]},
         "bpm": {"type": "number", "description": "Solo per set_tempo"}},
      "required": ["action"]}},
    {"name": "fire", "description": "Lancia o ferma scene e clip nella Session View.",
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["scene", "clip", "stop_clip", "stop_all"]},
         "track": {"type": "integer"}, "index": {"type": "integer", "description": "Indice scena o clip slot"}},
      "required": ["what"]}},
    {"name": "mixer", "description": "Mixer: volume (0-1), pan (-1..1), send (0-1), mute/solo/arm per traccia.",
     "input_schema": {"type": "object", "properties": {
         "track": {"type": "integer"},
         "param": {"type": "string", "enum": ["volume", "pan", "send", "mute", "solo", "arm"]},
         "value": {"type": "number"}, "send_index": {"type": "integer"}},
      "required": ["track", "param", "value"]}},
    {"name": "device_param", "description": "Imposta un parametro (0-1 normalizzato) di un device su una traccia, incluse le macro dei rack (param 1-8 nei rack).",
     "input_schema": {"type": "object", "properties": {
         "track": {"type": "integer"}, "device": {"type": "integer"},
         "param": {"type": "integer"}, "value": {"type": "number"}},
      "required": ["track", "device", "param", "value"]}},
    {"name": "create", "description": "Crea tracce MIDI/audio o clip MIDI (length in beats).",
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["midi_track", "audio_track", "midi_clip"]},
         "track": {"type": "integer"}, "clip": {"type": "integer"}, "length_beats": {"type": "number"}},
      "required": ["what"]}},
    {"name": "delete_track", "description": "Elimina una o piu tracce per indice (0-based). Passa track (int) oppure tracks (lista di int). Le tracce vengono eliminate dall'indice piu alto al piu basso per non far slittare gli indici. Operazione distruttiva.",
     "input_schema": {"type": "object", "properties": {
         "track": {"type": "integer"}, "tracks": {"type": "array", "items": {"type": "integer"}}},
      "required": []}},
    {"name": "write_notes", "description": "Scrive note MIDI in una clip: lista di {pitch, start, duration, velocity}. start/duration in beats.",
     "input_schema": {"type": "object", "properties": {
         "track": {"type": "integer"}, "clip": {"type": "integer"},
         "notes": {"type": "array", "items": {"type": "object", "properties": {
             "pitch": {"type": "integer"}, "start": {"type": "number"},
             "duration": {"type": "number"}, "velocity": {"type": "integer"}},
             "required": ["pitch", "start", "duration"]}}},
      "required": ["track", "clip", "notes"]}},
    {"name": "ableton", "description": "Controlla il processo Ableton Live e i progetti: status, find_exe, launch, quit, open_project, save, list_projects. Serve per riavviare Live quando un plugin deve rileggere le sue cartelle preset.",
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["status", "find_exe", "launch", "quit",
                                                "open_project", "save", "list_projects"]},
         "project": {"type": "string"}, "path": {"type": "string"},
         "root": {"type": "string"}, "limit": {"type": "integer"},
         "force": {"type": "boolean"}, "restart": {"type": "boolean"}},
         "required": ["action"]}},
    {"name": "get_state", "description": "Legge lo stato del progetto: tempo, tracce, device di una traccia, parametri di un device.",
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["snapshot", "devices", "device_params"]},
         "track": {"type": "integer"}, "device": {"type": "integer"}},
      "required": ["what"]}},
    {"name": "set_param_by_name", "description": "Imposta un parametro di un device/VST cercandolo per NOME (fuzzy). Usa get_state device_params prima se vuoi vedere i nomi esatti. value normalizzato 0-1.",
     "input_schema": {"type": "object", "properties": {
         "track": {"type": "integer"}, "device": {"type": "integer"},
         "param_name": {"type": "string"}, "value": {"type": "number"}},
      "required": ["track", "device", "param_name", "value"]}},
    {"name": "load_device", "description": "Carica un device o VST dal browser di Live sulla traccia indicata (es. 'Acid V', 'Serum', 'Operator'). Automatizza la UI: Live deve essere visibile, viene caricato il PRIMO risultato della ricerca. Verifica poi con get_state devices.",
     "input_schema": {"type": "object", "properties": {
         "track": {"type": "integer"}, "device_name": {"type": "string"}},
      "required": ["track", "device_name"]}},
    {"name": "arrangement", "description": "Lavora nella vista Arrangement: sposta la playhead (beats), loop region, punch in/out, locatori (cue), registrazione in arrangement, back to arrangement, overdub. Per scrivere musica nell'arrangement: componi le clip in Session, poi record_start + fire delle clip = registrate sulla timeline.",
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["goto", "jump_by", "get_position", "loop_on", "loop_off", "set_loop_region", "punch", "add_cue_here", "next_cue", "prev_cue", "back_to_arrangement", "overdub_on", "overdub_off", "record_start", "record_stop"]},
         "beats": {"type": "number", "description": "Posizione o salto in beats (goto/jump_by)"},
         "start": {"type": "number"}, "length": {"type": "number"},
         "punch_in": {"type": "boolean"}, "punch_out": {"type": "boolean"}},
      "required": ["action"]}},
    {"name": "analyze_audio", "description": "Misura il master in tempo reale: LUFS integrato/short-term, true peak dBTP, bilanciamento spettrale. Usalo prima di giudizi su mix/master.",
     "input_schema": {"type": "object", "properties": {
         "seconds": {"type": "number", "description": "Durata della misura (default 8)"}},
      "required": []}},

    # ---- Layer OSC generico: copre l'intero address space AbletonOSC
    # (https://github.com/ideoforms/AbletonOSC) anche dove non c'e' una
    # convenience dedicata qui sotto. address = '/live/{namespace}/{get|set|method}/{property}'.
    {"name": "osc_get", "description": "GET grezzo su un address OSC AbletonOSC arbitrario. "
        "Copre l'intero address space: song, track, clip, device, clip_slot, scene, view, "
        "application. Esempi: '/live/track/get/color' [track_index]; "
        "'/live/clip/get/loop_start' [track, clip]; '/live/song/get/song_length' [].",
     "input_schema": {"type": "object", "properties": {
         "address": {"type": "string", "description": "Es. '/live/track/get/color'"},
         "args": {"type": "array", "items": {}, "description": "Indici posizionali richiesti dall'address (es. [track] o [track, clip]), in ordine"}},
      "required": ["address"]}},
    {"name": "osc_set", "description": "SET o CALL grezzo (fire-and-forget) su un address OSC "
        "arbitrario. Esempi: '/live/clip/set/name' [track, clip, 'Acid Loop']; "
        "'/live/clip/fire' [track, clip]; '/live/song/undo' [].",
     "input_schema": {"type": "object", "properties": {
         "address": {"type": "string", "description": "Es. '/live/clip/set/color_index'"},
         "args": {"type": "array", "items": {}, "description": "Argomenti posizionali dell'address, in ordine"}},
      "required": ["address"]}},

    {"name": "track_meta", "description": "Nome e colore di una traccia (non coperti da mixer).",
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["get_name", "set_name", "get_color", "set_color"]},
         "track": {"type": "integer"},
         "name": {"type": "string"}, "color": {"type": "integer", "description": "ARGB come intero"}},
      "required": ["action", "track"]}},

    {"name": "clip_property", "description": "Get/set di una proprieta' clip qualsiasi (name, color, "
        "color_index, loop_start, loop_end, looping, gain, pitch_coarse, pitch_fine, warping, "
        "warp_mode, muted, start_marker, end_marker, launch_mode, launch_quantization, legato...). "
        "Vedi API Clip di AbletonOSC per l'elenco completo.",
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["get", "set"]},
         "track": {"type": "integer"}, "clip": {"type": "integer"},
         "prop": {"type": "string"}, "value": {}},
      "required": ["action", "track", "clip", "prop"]}},

    {"name": "clip_notes_bulk", "description": "Legge o rimuove TUTTE le note MIDI di una clip in blocco "
        "(per aggiungere note usa write_notes).",
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["get", "remove"]},
         "track": {"type": "integer"}, "clip": {"type": "integer"}},
      "required": ["action", "track", "clip"]}},

    {"name": "clip_slot", "description": "Gestione clip slot: presenza clip, creazione/cancellazione, "
        "duplicazione tra slot (per costruire pattern senza registrare a mano).",
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["has_clip", "create_clip", "delete_clip", "duplicate_clip_to", "fire", "stop"]},
         "track": {"type": "integer"}, "clip": {"type": "integer"},
         "length_beats": {"type": "number", "description": "Solo per create_clip"},
         "dst_track": {"type": "integer", "description": "Solo per duplicate_clip_to"},
         "dst_clip": {"type": "integer", "description": "Solo per duplicate_clip_to"}},
      "required": ["action", "track", "clip"]}},

    {"name": "device_params_full", "description": "Elenco COMPLETO dei parametri di un device: nome, "
        "valore normalizzato 0-1, valore leggibile in unita' reali (es. '2500 Hz', '-6.0 dB'), min, max. "
        "Usalo per verificare un preset dopo averlo applicato con device_param, non solo per leggerlo.",
     "input_schema": {"type": "object", "properties": {
         "track": {"type": "integer"}, "device": {"type": "integer"}},
      "required": ["track", "device"]}},

    {"name": "scene_property", "description": "Get/set proprieta' di una scena: name, color, color_index, "
        "tempo, tempo_enabled, time_signature_numerator/denominator, time_signature_enabled.",
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["get", "set"]},
         "scene": {"type": "integer"}, "prop": {"type": "string"}, "value": {}},
      "required": ["action", "scene", "prop"]}},

    {"name": "view", "description": "Selezione UI corrente in Live: traccia, scena, device selezionati.",
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["get_selected_track", "set_selected_track",
                                                "get_selected_scene", "set_selected_scene",
                                                "get_selected_device", "set_selected_device"]},
         "track": {"type": "integer"}, "scene": {"type": "integer"}, "device": {"type": "integer"}},
      "required": ["action"]}},

    {"name": "song_action", "description": "Azioni a livello song non coperte da transport/arrangement: "
        "undo, redo, capture_midi (cattura da session ad arrangement), continue_playing, "
        "trigger_session_record, create_scene, delete_scene, duplicate_scene, get_num_scenes.",
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["undo", "redo", "capture_midi", "continue_playing",
                                                "trigger_session_record", "create_scene", "delete_scene",
                                                "duplicate_scene", "get_num_scenes"]},
         "index": {"type": "integer", "description": "Indice scena per create/delete/duplicate_scene (-1 = in coda)"}},
      "required": ["action"]}},

    {"name": "app_info", "description": "Diagnostica applicazione: versione Live (/live/application/get/version) "
        "e test di connettivita' di base (/live/test).",
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["version", "test"]}},
      "required": ["what"]}},

    # ---- Canale LiveMind (LOM diretta) — PREFERITO per nuovo lavoro: non
    # dipende da AbletonOSC, copre l'intera Live Object Model incluso quello
    # che OSC non espone (rack chains, automation envelope, Arrangement View
    # via duplicate_clip_to_arrangement, browser, freeze/flatten).
    {"name": "lom", "description": "Get/set/call/len/link generico sulla Live Object Model, via Remote "
        "Script LiveMind (canale diretto, non OSC). path = lista di step 'nome' o 'nome:indice', es. "
        "['tracks:0','devices:1','parameters:2']. Per Arrangement View: crea il clip in session "
        "(call su clip_slot, method 'create_clip'), poi call su track con method "
        "'duplicate_clip_to_arrangement', args=[{'__lom_ref__': path_del_clip}, tempo_in_beats]. "
        "'link' serve per assegnare un riferimento oggetto a una proprieta' (es. view.selected_track).",
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["ping", "get", "set", "call", "len", "link"]},
         "root": {"type": "string", "enum": ["song", "app"], "default": "song"},
         "path": {"type": "array", "items": {"type": "string"}},
         "prop": {"type": "string", "description": "get/set/link"},
         "value": {"description": "set"},
         "method": {"type": "string", "description": "call"},
         "args": {"type": "array", "items": {},
                   "description": "call — un item {'__lom_ref__': [...]} risolve un riferimento oggetto invece di un valore JSON"},
         "value_path": {"type": "array", "items": {"type": "string"}, "description": "link"}},
      "required": ["action"]}},

    {"name": "knowledge", "description": "Knowledge base di LIVEMIND (docs/knowledge): mastering, Ozone 11 "
        "modulo per modulo, Voxengo SPAN Plus, compressione, effetti sui return. action: topics | read(topic) | "
        "search(query) | ozone_chain(genre: hardtek/tekno_tribe/acid/hardflor, destination: club/streaming) | "
        "delay_ms(bpm, division es. '1/8d', '1/16t'). Consultala prima di decisioni di mix/master.",
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["topics", "read", "search", "ozone_chain", "delay_ms"]},
         "topic": {"type": "string"}, "query": {"type": "string"},
         "max_hits": {"type": "integer", "default": 3},
         "genre": {"type": "string"}, "destination": {"type": "string", "default": "club"},
         "bpm": {"type": "number"}, "division": {"type": "string", "default": "1/4"}},
      "required": ["action"]}},

    {"name": "run", "description": "Esegue un comando shell (cmd.exe) sulla macchina dell'utente — "
        "robocopy, git, python, o qualunque comando utile. Nessun popup di conferma.",
     "input_schema": {"type": "object", "properties": {
         "command": {"type": "string"}, "cwd": {"type": "string"},
         "timeout": {"type": "integer", "default": 120}},
      "required": ["command"]}},
]


def _dispatch_lom(args: dict, lom) -> str:
    if lom is None:
        return "canale LOM non disponibile (Remote Script LiveMind non raggiunge 127.0.0.1:9005)"
    a = args["action"]
    root = args.get("root", "song")
    path = args.get("path")
    if a == "ping":
        r = lom.ping()
    elif a == "get":
        r = lom.get(path, args["prop"], root=root)
    elif a == "set":
        r = lom.set(path, args["prop"], args.get("value"), root=root)
    elif a == "call":
        r = lom.call(path, args["method"], args.get("args"), root=root)
    elif a == "len":
        r = lom.length(path, root=root)
    elif a == "link":
        r = lom.link(path, args["prop"], args.get("value_path"), root=root)
    else:
        return f"azione lom sconosciuta: {a}"
    return str(r)


def dispatch(name: str, args: dict[str, Any], live, analyzer=None, loader=None, lom=None) -> str:
    """Esegue un tool call sul LiveController. Ritorna testo per il modello."""
    try:
        if name == "transport":
            a = args["action"]
            if a == "play": live.play()
            elif a == "stop": live.stop()
            elif a == "record_on": live.record(True)
            elif a == "record_off": live.record(False)
            elif a == "metronome_on": live.metronome(True)
            elif a == "metronome_off": live.metronome(False)
            elif a == "set_tempo": live.set_tempo(args["bpm"])
            return f"transport {a} ok"
        if name == "fire":
            w = args["what"]
            if w == "scene": live.fire_scene(args["index"])
            elif w == "clip": live.fire_clip(args["track"], args["index"])
            elif w == "stop_clip": live.stop_clip(args["track"], args["index"])
            elif w == "stop_all": live.stop_all_clips()
            return f"fire {w} ok"
        if name == "mixer":
            t, p, v = args["track"], args["param"], args["value"]
            if p == "volume": live.set_volume(t, v)
            elif p == "pan": live.set_pan(t, v)
            elif p == "send": live.set_send(t, args.get("send_index", 0), v)
            elif p == "mute": live.mute(t, bool(v))
            elif p == "solo": live.solo(t, bool(v))
            elif p == "arm": live.arm(t, bool(v))
            return f"mixer track {t} {p}={v} ok"
        if name == "device_param":
            live.set_device_param(args["track"], args["device"], args["param"], args["value"])
            return "device_param ok"
        if name == "create":
            w = args["what"]
            if w == "midi_track": live.create_midi_track(args.get("track", -1))
            elif w == "audio_track": live.create_audio_track(args.get("track", -1))
            elif w == "midi_clip": live.create_clip(args["track"], args["clip"], args.get("length_beats", 4.0))
            return f"create {w} ok"
        if name == "delete_track":
            idxs = args.get("tracks")
            if idxs is None:
                idxs = [args["track"]]
            order = sorted({int(x) for x in idxs}, reverse=True)  # alto->basso: gli indici non slittano
            for i in order:
                live.delete_track(i)
            return f"eliminate tracce (index) {order}"
        if name == "write_notes":
            live.add_notes(args["track"], args["clip"], args["notes"])
            return f"scritte {len(args['notes'])} note"
        if name == "get_state":
            w = args["what"]
            if w == "snapshot": return str(live.snapshot())
            if w == "devices": return str(live.get_devices(args["track"]))
            if w == "device_params":
                names = live.get_device_params(args["track"], args["device"]) or ()
                values = live.get_param_values(args["track"], args["device"]) or ()
                pairs = [f"{i}:{n}={v}" for i, (n, v) in enumerate(zip(names[2:], values[2:]))]
                return "; ".join(pairs) if pairs else "nessun parametro (device vuoto o indice errato)"
            return f"get_state: 'what' non valido: {w} (usa snapshot|devices|device_params)"
        if name == "set_param_by_name":
            from livemind.osc.paramfind import find_param
            names = live.get_device_params(args["track"], args["device"]) or ()
            names = list(names[2:])  # i primi 2 elementi sono track/device id
            idx = find_param([str(n) for n in names], args["param_name"])
            if idx is None:
                return f"parametro '{args['param_name']}' non trovato tra: {names[:40]}"
            live.set_device_param(args["track"], args["device"], idx, args["value"])
            return f"impostato '{names[idx]}' (index {idx}) = {args['value']}"
        if name == "load_device":
            if loader is None:
                return "loader UI non disponibile (pip install pyautogui pygetwindow)"
            # la selezione via OSC e' opzionale: se AbletonOSC non e' attivo si
            # carica comunque sulla traccia gia' selezionata (via lom link)
            try:
                live.select_track(args["track"])
            except Exception:
                pass
            import time; time.sleep(0.2)
            return loader.load(args["device_name"])
        if name == "arrangement":
            a = args["action"]
            if a == "goto": live.goto_time(args["beats"])
            elif a == "jump_by": live.jump_by(args["beats"])
            elif a == "get_position": return f"posizione: {live.get_time()} beats"
            elif a == "loop_on": live.set_loop(True)
            elif a == "loop_off": live.set_loop(False)
            elif a == "set_loop_region": live.set_loop_region(args["start"], args["length"])
            elif a == "punch": live.punch(args.get("punch_in", False), args.get("punch_out", False))
            elif a == "add_cue_here": live.add_cue()
            elif a == "next_cue": live.jump_cue(True)
            elif a == "prev_cue": live.jump_cue(False)
            elif a == "back_to_arrangement": live.back_to_arranger()
            elif a == "overdub_on": live.arrangement_overdub(True)
            elif a == "overdub_off": live.arrangement_overdub(False)
            elif a == "record_start":
                live.record(True); live.play()
            elif a == "record_stop":
                live.record(False); live.stop()
            return f"arrangement {a} ok"
        if name == "analyze_audio":
            if analyzer is None:
                return "analyzer non disponibile (loopback audio non configurato)"
            return str(analyzer.measure(args.get("seconds", 8)))
        if name == "osc_get":
            r = live.osc_get(args["address"], *args.get("args", []))
            return str(r) if r is not None else "nessuna risposta (timeout o address errato)"
        if name == "osc_set":
            live.osc_set(args["address"], *args.get("args", []))
            return f"inviato {args['address']} {args.get('args', [])}"
        if name == "track_meta":
            a, t = args["action"], args["track"]
            if a == "get_name": return f"traccia {t}: {live.get_track_name(t)}"
            if a == "set_name": live.set_track_name(t, args["name"]); return f"traccia {t} rinominata '{args['name']}'"
            if a == "get_color": return f"traccia {t} colore: {live.get_track_color(t)}"
            if a == "set_color": live.set_track_color(t, args["color"]); return f"traccia {t} colore impostato"
        if name == "clip_property":
            a, tr, cl, p = args["action"], args["track"], args["clip"], args["prop"]
            if a == "get":
                r = live.get_clip_property(tr, cl, p)
                return str(r) if r is not None else f"nessuna risposta per '{p}'"
            live.set_clip_property(tr, cl, p, args["value"])
            return f"clip [{tr},{cl}] {p} = {args['value']}"
        if name == "clip_notes_bulk":
            a, tr, cl = args["action"], args["track"], args["clip"]
            if a == "get":
                r = live.get_clip_notes(tr, cl)
                return str(r) if r is not None else "nessuna nota o nessuna risposta"
            live.remove_clip_notes(tr, cl)
            return f"note rimosse da clip [{tr},{cl}]"
        if name == "clip_slot":
            a, tr, cl = args["action"], args["track"], args["clip"]
            if a == "has_clip": return f"has_clip [{tr},{cl}]: {live.clip_slot_has_clip(tr, cl)}"
            if a == "create_clip":
                live.clip_slot_create_clip(tr, cl, args.get("length_beats", 4.0))
                return f"clip creata in [{tr},{cl}]"
            if a == "delete_clip":
                live.clip_slot_delete_clip(tr, cl)
                return f"clip cancellata in [{tr},{cl}]"
            if a == "duplicate_clip_to":
                live.clip_slot_duplicate_clip_to(tr, cl, args["dst_track"], args["dst_clip"])
                return f"clip duplicata [{tr},{cl}] -> [{args['dst_track']},{args['dst_clip']}]"
            if a == "fire": live.fire_clip_direct(tr, cl); return f"fire [{tr},{cl}] ok"
            if a == "stop": live.stop_clip(tr, cl); return f"stop [{tr},{cl}] ok"
        if name == "device_params_full":
            params = live.get_device_params_full(args["track"], args["device"])
            if not params:
                return "nessun parametro (device vuoto o indice errato)"
            return "; ".join(
                f"{p['index']}:{p['name']}={p['value']} ({p['value_string']}) [{p['min']}..{p['max']}]"
                for p in params
            )
        if name == "scene_property":
            a, sc, p = args["action"], args["scene"], args["prop"]
            if a == "get":
                r = live.get_scene_property(sc, p)
                return str(r) if r is not None else f"nessuna risposta per '{p}'"
            live.set_scene_property(sc, p, args["value"])
            return f"scena {sc} {p} = {args['value']}"
        if name == "view":
            a = args["action"]
            if a == "get_selected_track": return f"traccia selezionata: {live.get_selected_track()}"
            if a == "set_selected_track": live.set_selected_track_view(args["track"]); return "ok"
            if a == "get_selected_scene": return f"scena selezionata: {live.get_selected_scene()}"
            if a == "set_selected_scene": live.set_selected_scene_view(args["scene"]); return "ok"
            if a == "get_selected_device": return f"device selezionato: {live.get_selected_device()}"
            if a == "set_selected_device":
                live.set_selected_device_view(args["track"], args["device"]); return "ok"
        if name == "song_action":
            a = args["action"]
            if a == "undo": live.undo(); return "undo ok"
            if a == "redo": live.redo(); return "redo ok"
            if a == "capture_midi": live.capture_midi(); return "capture_midi ok"
            if a == "continue_playing": live.continue_playing(); return "continue_playing ok"
            if a == "trigger_session_record": live.trigger_session_record(); return "trigger_session_record ok"
            if a == "create_scene": live.create_scene(args.get("index", -1)); return "scena creata"
            if a == "delete_scene": live.delete_scene(args["index"]); return f"scena {args['index']} eliminata"
            if a == "duplicate_scene": live.duplicate_scene(args["index"]); return f"scena {args['index']} duplicata"
            if a == "get_num_scenes": return f"num_scenes: {live.get_num_scenes()}"
        if name == "app_info":
            w = args["what"]
            if w == "version": return f"Live version: {live.get_application_version()}"
            if w == "test": return f"test: {live.test_connection()}"
        if name == "kick3_ui":
            from livemind.presets.kick3_ui import dispatch as k3_dispatch
            return k3_dispatch(args)
        if name == "ableton":
            from livemind.ableton_ctl import dispatch as ableton_dispatch
            return ableton_dispatch(args)
        if name == "lom":
            return _dispatch_lom(args, lom)
        if name == "knowledge":
            from livemind.brain.kb import dispatch as kb_dispatch
            return kb_dispatch(args)
        if name == "run":
            from livemind.local_exec_mcp import build_tools
            return build_tools()["run"](args["command"], args.get("cwd"), args.get("timeout", 120))
        return f"tool sconosciuto: {name}"
    except Exception as e:  # il brain deve sapere cosa è fallito
        return f"ERRORE {name}: {e}"
