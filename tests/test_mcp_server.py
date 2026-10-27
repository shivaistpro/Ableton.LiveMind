"""Test del layer MCP sincrono: build_tools() e' pura Python, nessuna rete e
nessun pacchetto 'mcp' richiesto (l'import di FastMCP e' isolato in create_server,
mai chiamato qui). Riusa FakeLive dallo stile di test_tools.py."""
from livemind.mcp_server import build_tools


class FakeLive:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def rec(*a, **k):
            self.calls.append((name, a))
            if name == "snapshot":
                return {"tempo": 140.0, "tracks": ["Kick"], "num_tracks": 1}
            return None
        return rec


def test_build_tools_exposes_all_expected_names():
    tools = build_tools(FakeLive())
    expected = {
        "transport", "fire", "mixer", "device_param", "set_param_by_name",
        "create", "delete_track", "write_notes", "get_state", "load_device",
        "arrangement", "analyze_audio", "connection_status",
        "osc_get", "osc_set", "track_meta", "clip_property", "clip_notes_bulk",
        "clip_slot", "device_params_full", "scene_property", "view",
        "song_action", "app_info",
    }
    assert expected == set(tools.keys())


def test_transport_set_tempo():
    live = FakeLive()
    tools = build_tools(live)
    out = tools["transport"](action="set_tempo", bpm=170)
    assert "ok" in out
    assert ("set_tempo", (170,)) in live.calls


def test_transport_play_without_bpm():
    live = FakeLive()
    tools = build_tools(live)
    out = tools["transport"](action="play")
    assert "ok" in out
    assert ("play", ()) in live.calls


def test_mixer_volume():
    live = FakeLive()
    tools = build_tools(live)
    tools["mixer"](track=2, param="volume", value=0.8)
    assert ("set_volume", (2, 0.8)) in live.calls


def test_device_param_forwards_indices():
    live = FakeLive()
    tools = build_tools(live)
    tools["device_param"](track=1, device=0, param=3, value=0.42)
    assert ("set_device_param", (1, 0, 3, 0.42)) in live.calls


def test_set_param_by_name_uses_fuzzy_lookup():
    class Live(FakeLive):
        def get_device_params(self, track, device):
            return ("track_id", "device_id", "Start Freq", "Decay", "Drive")

    live = Live()
    tools = build_tools(live)
    out = tools["set_param_by_name"](track=0, device=0, param_name="decay", value=0.5)
    assert "Decay" in out
    assert ("set_device_param", (0, 0, 1, 0.5)) in live.calls


def test_load_device_forwards_to_loader():
    class FakeLoader:
        def load(self, name):
            return f"caricato {name}"

    live = FakeLive()
    tools = build_tools(live, loader=FakeLoader())
    out = tools["load_device"](track=0, device_name="KICK 3")
    assert "caricato KICK 3" in out
    assert ("select_track", (0,)) in live.calls


def test_load_device_without_loader_reports_missing():
    live = FakeLive()
    tools = build_tools(live, loader=None)
    out = tools["load_device"](track=0, device_name="KICK 3")
    assert "loader" in out.lower()


def test_write_notes_count():
    live = FakeLive()
    tools = build_tools(live)
    notes = [{"pitch": 57, "start": 0, "duration": 0.25}]
    out = tools["write_notes"](track=1, clip=0, notes=notes)
    assert "1 note" in out


def test_get_state_snapshot():
    live = FakeLive()
    tools = build_tools(live)
    out = tools["get_state"](what="snapshot")
    assert "140" in out


def test_arrangement_set_loop_region():
    live = FakeLive()
    tools = build_tools(live)
    tools["arrangement"](action="set_loop_region", start=32, length=16)
    assert ("set_loop_region", (32, 16)) in live.calls


def test_delete_track_multi_high_to_low():
    live = FakeLive()
    tools = build_tools(live)
    tools["delete_track"](tracks=[5, 6, 12, 8])
    deleted = [a[0] for (n, a) in live.calls if n == "delete_track"]
    assert deleted == [12, 8, 6, 5]


def test_connection_status_ok():
    live = FakeLive()
    tools = build_tools(live)
    out = tools["connection_status"]()
    assert "connesso" in out
    assert "140" in out


def test_connection_status_not_responding():
    class DeadLive(FakeLive):
        def snapshot(self):
            return {"tempo": None, "tracks": [], "num_tracks": 0}

    tools = build_tools(DeadLive())
    out = tools["connection_status"]()
    assert "NON risponde" in out


def test_connection_status_raises_is_caught():
    class BrokenLive(FakeLive):
        def snapshot(self):
            raise ConnectionRefusedError("porta chiusa")

    tools = build_tools(BrokenLive())
    out = tools["connection_status"]()
    assert out.startswith("ERRORE")


def test_analyze_audio_missing_analyzer():
    live = FakeLive()
    tools = build_tools(live, analyzer=None)
    out = tools["analyze_audio"]()
    assert "non disponibile" in out


# ---- Layer OSC generico ----

def test_osc_get_forwards_address_and_args():
    class Live(FakeLive):
        def osc_get(self, address, *a):
            self.calls.append(("osc_get", (address, a)))
            return (0, 5920893)
    live = Live()
    tools = build_tools(live)
    out = tools["osc_get"](address="/live/track/get/color", args=[0])
    assert "5920893" in out
    assert ("osc_get", ("/live/track/get/color", (0,))) in live.calls


def test_osc_get_no_response():
    live = FakeLive()  # osc_get -> None di default
    tools = build_tools(live)
    out = tools["osc_get"](address="/live/song/get/song_length")
    assert "nessuna risposta" in out


def test_osc_set_forwards_and_reports():
    live = FakeLive()
    tools = build_tools(live)
    out = tools["osc_set"](address="/live/clip/fire", args=[0, 2])
    assert ("osc_set", ("/live/clip/fire", 0, 2)) in live.calls
    assert "/live/clip/fire" in out


# ---- track_meta ----

def test_track_meta_set_name():
    live = FakeLive()
    tools = build_tools(live)
    out = tools["track_meta"](action="set_name", track=1, name="Kick Hard")
    assert ("set_track_name", (1, "Kick Hard")) in live.calls
    assert "Kick Hard" in out


def test_track_meta_get_color():
    class Live(FakeLive):
        def get_track_color(self, track):
            return 5920893
    tools = build_tools(Live())
    out = tools["track_meta"](action="get_color", track=0)
    assert "5920893" in out


# ---- clip_property ----

def test_clip_property_set():
    live = FakeLive()
    tools = build_tools(live)
    out = tools["clip_property"](action="set", track=0, clip=0, prop="loop_end", value=8.0)
    assert ("set_clip_property", (0, 0, "loop_end", 8.0)) in live.calls
    assert "loop_end" in out


def test_clip_property_get():
    class Live(FakeLive):
        def get_clip_property(self, track, clip, prop):
            return (track, clip, 4.0)
    tools = build_tools(Live())
    out = tools["clip_property"](action="get", track=0, clip=0, prop="loop_start")
    assert "4.0" in out


# ---- clip_notes_bulk ----

def test_clip_notes_bulk_remove():
    live = FakeLive()
    tools = build_tools(live)
    out = tools["clip_notes_bulk"](action="remove", track=1, clip=0)
    assert ("remove_clip_notes", (1, 0)) in live.calls
    assert "rimosse" in out


# ---- clip_slot ----

def test_clip_slot_create_clip():
    live = FakeLive()
    tools = build_tools(live)
    out = tools["clip_slot"](action="create_clip", track=0, clip=1, length_beats=4.0)
    assert ("clip_slot_create_clip", (0, 1, 4.0)) in live.calls
    assert "creata" in out


def test_clip_slot_has_clip():
    class Live(FakeLive):
        def clip_slot_has_clip(self, track, clip):
            return True
    tools = build_tools(Live())
    out = tools["clip_slot"](action="has_clip", track=0, clip=0)
    assert "True" in out


def test_clip_slot_duplicate_clip_to():
    live = FakeLive()
    tools = build_tools(live)
    out = tools["clip_slot"](action="duplicate_clip_to", track=0, clip=0, dst_track=1, dst_clip=2)
    assert ("clip_slot_duplicate_clip_to", (0, 0, 1, 2)) in live.calls


# ---- device_params_full ----

def test_device_params_full_formats_readable_values():
    class Live(FakeLive):
        def get_device_params_full(self, track, device):
            return [
                {"index": 0, "name": "Start Freq", "value": 0.42,
                 "value_string": "260 Hz", "min": 20.0, "max": 500.0},
                {"index": 1, "name": "Decay", "value": 0.3,
                 "value_string": "38 ms", "min": 1.0, "max": 500.0},
            ]
    tools = build_tools(Live())
    out = tools["device_params_full"](track=0, device=0)
    assert "260 Hz" in out and "Start Freq" in out
    assert "38 ms" in out


def test_device_params_full_empty():
    class Live(FakeLive):
        def get_device_params_full(self, track, device):
            return []
    tools = build_tools(Live())
    out = tools["device_params_full"](track=0, device=0)
    assert "nessun parametro" in out


# ---- scene_property ----

def test_scene_property_set_tempo():
    live = FakeLive()
    tools = build_tools(live)
    out = tools["scene_property"](action="set", scene=0, prop="tempo", value=170.0)
    assert ("set_scene_property", (0, "tempo", 170.0)) in live.calls
    assert "170.0" in out


# ---- view ----

def test_view_get_selected_track():
    class Live(FakeLive):
        def get_selected_track(self):
            return 2
    tools = build_tools(Live())
    out = tools["view"](action="get_selected_track")
    assert "2" in out


def test_view_set_selected_device():
    live = FakeLive()
    tools = build_tools(live)
    out = tools["view"](action="set_selected_device", track=0, device=1)
    assert ("set_selected_device_view", (0, 1)) in live.calls


# ---- song_action ----

def test_song_action_undo():
    live = FakeLive()
    tools = build_tools(live)
    out = tools["song_action"](action="undo")
    assert ("undo", ()) in live.calls
    assert "ok" in out


def test_song_action_create_scene_default_index():
    live = FakeLive()
    tools = build_tools(live)
    tools["song_action"](action="create_scene")
    assert ("create_scene", (-1,)) in live.calls


def test_song_action_delete_scene_with_index():
    live = FakeLive()
    tools = build_tools(live)
    tools["song_action"](action="delete_scene", index=3)
    assert ("delete_scene", (3,)) in live.calls


# ---- app_info ----

def test_app_info_version():
    class Live(FakeLive):
        def get_application_version(self):
            return (12, 1)
    tools = build_tools(Live())
    out = tools["app_info"](what="version")
    assert "12" in out and "1" in out


def test_app_info_test_connection():
    class Live(FakeLive):
        def test_connection(self):
            return ("ok",)
    tools = build_tools(Live())
    out = tools["app_info"](what="test")
    assert "ok" in out
