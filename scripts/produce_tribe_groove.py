"""Produzione automatica: groove tribe/hardtekno a 150 BPM — kick 909 aperto e
rombante + basso caldo in sincope, drive industrial/trance, mixing di base.

Canale LiveMind/LOM diretto (NON AbletonOSC): remote_script/LiveMind deve
essere selezionato in Ableton come Control Surface (vedi README.md). Il
caricamento device resta via DeviceLoader (pyautogui, indipendente da OSC).

Esegui da CMD:
  cd /d "<LIVEMIND_DIR>"
  python scripts\produce_tribe_groove.py
"""
from __future__ import annotations
import sys
import time

from livemind.lom_client import LomClient
from livemind.osc.loader import DeviceLoader
from livemind.osc.paramfind import find_param

BPM = 150.0
BARS = 20
BEATS_PER_BAR = 4
TOTAL_BEATS = BARS * BEATS_PER_BAR  # 80 beat = 32.0s a 150 BPM ("circa 30 sec")

KICK_NOTE = 36
BASS_ROOT = 36
BASS_TURNAROUND = 43


def log(msg: str) -> None:
    print(f"[groove] {msg}")


def ok(r: dict):
    if not r.get("ok"):
        raise RuntimeError(r.get("error", r))
    return r.get("value")


def track_path(track: int) -> list:
    return ["tracks:%d" % track]


def device_path(track: int, device: int) -> list:
    return track_path(track) + ["devices:%d" % device]


def list_param_names(client: LomClient, dev_path: list) -> list[str]:
    n = client.length(dev_path + ["parameters"])
    if not n.get("ok"):
        return []
    names = []
    for i in range(n["value"]):
        r = client.get(dev_path + ["parameters:%d" % i], "name")
        names.append(str(r.get("value", "")) if r.get("ok") else "")
    return names


def set_by_name(client: LomClient, dev_path: list, names: list, query: str, value: float, report: list) -> None:
    idx = find_param(names, query)
    if idx is None:
        report.append((query, f"FALLITO: nessun match tra {len(names)} parametri"))
        return
    r = client.set(dev_path + ["parameters:%d" % idx], "value", value)
    report.append((query, f"OK -> '{names[idx]}' (idx {idx}) = {value}" if r.get("ok") else f"FALLITO: {r.get('error')}"))


def dump_params(client: LomClient, dev_path: list, label: str) -> None:
    names = list_param_names(client, dev_path)
    if not names:
        log(f"  [{label}] nessun parametro letto")
        return
    log(f"  [{label}] {len(names)} parametri:")
    for i, name in enumerate(names):
        r = client.get(dev_path + ["parameters:%d" % i], "value")
        log(f"    {i:>2} {name:<28} = {r.get('value') if r.get('ok') else '?'}")


def build_kick_notes() -> list[dict]:
    return [
        {"pitch": KICK_NOTE, "start_time": float(beat), "duration": 0.12, "velocity": 122}
        for beat in range(TOTAL_BEATS)
    ]


def build_bass_notes() -> list[dict]:
    notes = []
    offsets = [0.75, 1.75, 2.75, 3.75]  # sincope: ultima 16esima prima del kick successivo
    for bar in range(BARS):
        base = bar * BEATS_PER_BAR
        for i, off in enumerate(offsets):
            pitch = BASS_TURNAROUND if (bar in (7, 15) and i == 3) else BASS_ROOT
            notes.append({"pitch": pitch, "start_time": base + off, "duration": 0.2, "velocity": 100})
    return notes


def select_track(client: LomClient, track: int) -> None:
    client.link(["view"], "selected_track", track_path(track))
    time.sleep(0.2)


def load_device_safe(loader: DeviceLoader, client: LomClient, track: int, device_name: str, label: str) -> None:
    select_track(client, track)
    log(f"carico {device_name} su {label} (traccia {track})...")
    try:
        res = loader.load(device_name)
        log(f"  -> {res}")
    except Exception as e:
        log(f"  ERRORE caricamento {device_name} su {label}: {e}")
    time.sleep(0.8)


def main() -> None:
    log("connessione al Remote Script LiveMind...")
    client = LomClient()

    ping = client.ping()
    if not ping.get("ok"):
        log(f"ERRORE: {ping.get('error')}")
        log("Verifica che 'LiveMind' sia selezionato in Live > Preferences > Control Surface.")
        sys.exit(1)

    base_track_count = ok(client.length(["tracks"]))
    log(f"tracce esistenti: {base_track_count}")

    log(f"imposto tempo a {BPM} BPM")
    client.set([], "tempo", BPM)

    # ---- Tracce (indice esplicito = fine lista, niente sentinella -1) ----
    log("creo traccia Kick 909...")
    client.call([], "create_midi_track", [base_track_count])
    time.sleep(0.4)
    log("creo traccia Tribe Bass...")
    client.call([], "create_midi_track", [base_track_count + 1])
    time.sleep(0.4)

    kick_track = base_track_count
    bass_track = base_track_count + 1
    client.set(track_path(kick_track), "name", "Kick 909")
    client.set(track_path(bass_track), "name", "Tribe Bass")
    log(f"Kick 909 = traccia {kick_track}, Tribe Bass = traccia {bass_track}")

    # ---- Strumento: Operator su entrambe (kick 909-style via pitch envelope) ----
    loader = DeviceLoader()
    load_device_safe(loader, client, kick_track, "Operator", "Kick 909")
    load_device_safe(loader, client, bass_track, "Operator", "Tribe Bass")
    time.sleep(0.5)

    # ---- Sound design Kick 909 (device 0 = Operator) ----
    log("shaping Kick 909 (Operator: pitch drop + decay lungo = aperto/rombante)...")
    kd_path = device_path(kick_track, 0)
    names = list_param_names(client, kd_path)
    report = []
    set_by_name(client, kd_path, names, "volume", 0.75, report)
    set_by_name(client, kd_path, names, "pitch env amount", 0.15, report)
    set_by_name(client, kd_path, names, "pitch env time", 0.15, report)
    set_by_name(client, kd_path, names, "filter freq", 0.35, report)
    set_by_name(client, kd_path, names, "filter resonance", 0.2, report)
    set_by_name(client, kd_path, names, "decay", 0.55, report)
    set_by_name(client, kd_path, names, "release", 0.5, report)
    set_by_name(client, kd_path, names, "attack", 0.0, report)
    for q, r in report:
        log(f"  Kick '{q}': {r}")

    # ---- Sound design Tribe Bass ----
    log("shaping Tribe Bass (Operator: filtro chiuso, caldo)...")
    bd_path = device_path(bass_track, 0)
    names = list_param_names(client, bd_path)
    report = []
    set_by_name(client, bd_path, names, "volume", 0.65, report)
    set_by_name(client, bd_path, names, "filter freq", 0.22, report)
    set_by_name(client, bd_path, names, "filter resonance", 0.15, report)
    set_by_name(client, bd_path, names, "attack", 0.0, report)
    set_by_name(client, bd_path, names, "decay", 0.4, report)
    set_by_name(client, bd_path, names, "sustain", 0.6, report)
    set_by_name(client, bd_path, names, "release", 0.3, report)
    for q, r in report:
        log(f"  Bass '{q}': {r}")

    # ---- Drive industrial/trance: Overdrive dopo il synth ----
    load_device_safe(loader, client, kick_track, "Overdrive", "Kick 909")
    load_device_safe(loader, client, bass_track, "Overdrive", "Tribe Bass")
    time.sleep(0.5)

    log("applico drive (industrial, moderato: 'un po'')...")
    od_kick_path = device_path(kick_track, 1)
    od_bass_path = device_path(bass_track, 1)
    names_kick_od = list_param_names(client, od_kick_path)
    names_bass_od = list_param_names(client, od_bass_path)
    report = []
    set_by_name(client, od_kick_path, names_kick_od, "drive", 0.35, report)
    set_by_name(client, od_kick_path, names_kick_od, "tone", 0.55, report)
    set_by_name(client, od_bass_path, names_bass_od, "drive", 0.25, report)
    set_by_name(client, od_bass_path, names_bass_od, "tone", 0.5, report)
    for q, r in report:
        log(f"  Overdrive '{q}': {r}")

    # ---- Mixing: EQ Eight in coda catena (shaping fine nel prossimo giro) ----
    load_device_safe(loader, client, kick_track, "EQ Eight", "Kick 909")
    load_device_safe(loader, client, bass_track, "EQ Eight", "Tribe Bass")

    # ---- Mixer: gain staging conservativo (headroom, no clip senza metering) ----
    client.set(track_path(kick_track) + ["mixer_device", "volume"], "value", 0.78)
    client.set(track_path(kick_track) + ["mixer_device", "panning"], "value", 0.0)
    client.set(track_path(bass_track) + ["mixer_device", "volume"], "value", 0.68)
    client.set(track_path(bass_track) + ["mixer_device", "panning"], "value", 0.0)
    log("volumi/pan impostati (headroom conservativo)")

    # ---- Clip + note ----
    durata_s = TOTAL_BEATS * 60.0 / BPM
    log(f"creo clip da {TOTAL_BEATS} beat ({BARS} battute, {durata_s:.1f}s a {BPM} BPM)...")
    client.call(track_path(kick_track) + ["clip_slots:0"], "create_clip", [float(TOTAL_BEATS)])
    client.call(track_path(bass_track) + ["clip_slots:0"], "create_clip", [float(TOTAL_BEATS)])
    time.sleep(0.3)

    kick_clip = track_path(kick_track) + ["clip_slots:0", "clip"]
    bass_clip = track_path(bass_track) + ["clip_slots:0", "clip"]

    log("scrivo note Kick 909 (4/4 a ogni beat)...")
    client.call(kick_clip, "add_new_notes", [{"notes": build_kick_notes()}])
    log("scrivo note Tribe Bass (sincopato, root + quinta ogni 8 battute)...")
    client.call(bass_clip, "add_new_notes", [{"notes": build_bass_notes()}])

    client.set(kick_clip, "name", "Kick 909 groove")
    client.set(bass_clip, "name", "Tribe Bass groove")

    # ---- Dump completo parametri: base per il tuning di precisione ----
    time.sleep(0.5)
    log("=" * 60)
    log("DUMP PARAMETRI (per tuning esatto nel prossimo giro):")
    dump_params(client, device_path(kick_track, 0), "Kick 909 / Operator")
    dump_params(client, device_path(kick_track, 1), "Kick 909 / Overdrive")
    dump_params(client, device_path(kick_track, 2), "Kick 909 / EQ Eight")
    dump_params(client, device_path(bass_track, 0), "Tribe Bass / Operator")
    dump_params(client, device_path(bass_track, 1), "Tribe Bass / Overdrive")
    dump_params(client, device_path(bass_track, 2), "Tribe Bass / EQ Eight")

    log("=" * 60)
    log(f"RIEPILOGO: Kick 909 = traccia {kick_track}, Tribe Bass = traccia {bass_track}")
    log(f"tempo={BPM} BPM, {BARS} battute, durata={durata_s:.1f}s")
    log("Premi PLAY in Ableton. Incollami questo output completo: i FALLITO")
    log("sopra e il dump parametri mi dicono esattamente cosa correggere.")
    log("=" * 60)


if __name__ == "__main__":
    main()
