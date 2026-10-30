"""Test del dispatcher generico LOM (remote_script/LiveMind/lom.py).

Il modulo non importa ne' 'Live' ne' '_Framework': viene caricato per path
(bypassando il package reale, che invece richiede l'ambiente Ableton) e testato
con semplici oggetti Python al posto di Track/Device/Clip veri."""
import importlib.util
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[1] / "remote_script" / "LiveMind"


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, _ROOT / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lom = _load("livemind_remote_lom", "lom.py")


class FakeParam:
    def __init__(self, name, value=0.5):
        self.name = name
        self.value = value
        self.automation_state = 0

    def re_enable_automation(self):
        self.automation_state = 99


class FakeDevice:
    def __init__(self, name, params=None, chains=None):
        self.name = name
        self.parameters = params or []
        self.can_have_chains = chains is not None
        self.chains = chains or []


class FakeTrack:
    def __init__(self, name, devices=None):
        self.name = name
        self.devices = devices or []
        self.mute = False

    def rename(self, new_name):
        self.name = new_name
        return True


class FakeSong:
    def __init__(self, tracks):
        self.tracks = tracks
        self.tempo = 140.0

    def create_scene(self, index):
        return index


# ---- resolve / lom_get / lom_set / lom_call / lom_len ----

def test_resolve_empty_path_returns_root():
    song = FakeSong([])
    assert lom.resolve(song, []) is song
    assert lom.resolve(song, None) is song


def test_resolve_nested_path():
    dev = FakeDevice("EQ Eight")
    track = FakeTrack("Kick", devices=[dev])
    song = FakeSong([track])
    assert lom.resolve(song, ["tracks:0"]) is track
    assert lom.resolve(song, ["tracks:0", "devices:0"]) is dev


def test_resolve_rack_chain_path():
    inner_dev = FakeDevice("Operator")
    chain = FakeDevice("Chain 1", params=[], chains=None)
    chain.devices = [inner_dev]
    rack = FakeDevice("Instrument Rack", chains=[chain])
    track = FakeTrack("Lead", devices=[rack])
    song = FakeSong([track])
    resolved = lom.resolve(song, ["tracks:0", "devices:0", "chains:0", "devices:0"])
    assert resolved is inner_dev


def test_resolve_missing_attribute_raises():
    song = FakeSong([])
    with pytest.raises(lom.LomError):
        lom.resolve(song, ["nonexistent"])


def test_resolve_bad_index_raises():
    song = FakeSong([FakeTrack("Kick")])
    with pytest.raises(lom.LomError):
        lom.resolve(song, ["tracks:9"])


def test_lom_get_property():
    song = FakeSong([FakeTrack("Kick")])
    assert lom.lom_get(song, ["tracks:0"], "name") == "Kick"


def test_lom_get_missing_property_raises():
    song = FakeSong([FakeTrack("Kick")])
    with pytest.raises(lom.LomError):
        lom.lom_get(song, ["tracks:0"], "nonexistent")


def test_lom_set_property():
    track = FakeTrack("Kick")
    song = FakeSong([track])
    lom.lom_set(song, ["tracks:0"], "mute", True)
    assert track.mute is True


def test_lom_call_method_with_args():
    track = FakeTrack("Kick")
    song = FakeSong([track])
    result = lom.lom_call(song, ["tracks:0"], "rename", ["Kick Hard"])
    assert result is True
    assert track.name == "Kick Hard"


def test_lom_call_missing_method_raises():
    song = FakeSong([FakeTrack("Kick")])
    with pytest.raises(lom.LomError):
        lom.lom_call(song, ["tracks:0"], "nonexistent")


def test_lom_call_non_callable_raises():
    song = FakeSong([FakeTrack("Kick")])
    with pytest.raises(lom.LomError):
        lom.lom_call(song, ["tracks:0"], "name")  # 'name' e' una stringa, non un metodo


def test_lom_len():
    song = FakeSong([FakeTrack("Kick"), FakeTrack("Snare")])
    assert lom.lom_len(song, ["tracks"]) == 2


def test_lom_len_not_sizeable_raises():
    song = FakeSong([FakeTrack("Kick")])
    with pytest.raises(lom.LomError):
        lom.lom_len(song, ["tempo"])


# ---- automation_state: caso d'uso chiave che giustifica il nuovo layer ----

def test_automation_envelope_via_generic_path():
    param = FakeParam("Cutoff")
    dev = FakeDevice("Auto Filter", params=[param])
    track = FakeTrack("Bass", devices=[dev])
    song = FakeSong([track])
    path = ["tracks:0", "devices:0", "parameters:0"]
    assert lom.lom_get(song, path, "automation_state") == 0
    lom.lom_call(song, path, "re_enable_automation")
    assert lom.lom_get(song, path, "automation_state") == 99


# ---- dispatch() ----

def test_dispatch_ping():
    out = lom.dispatch({"cmd": "ping"}, get_song=lambda: None, get_app=lambda: None)
    assert out == {"ok": True, "pong": True}


def test_dispatch_batch_runs_all_and_keeps_errors_local():
    track = FakeTrack("Kick")
    song = FakeSong([track])
    out = lom.dispatch(
        {"cmd": "batch", "cmds": [
            {"cmd": "set", "path": ["tracks:0"], "prop": "mute", "value": True},
            {"cmd": "get", "path": ["tracks:9"], "prop": "name"},
            {"cmd": "get", "path": ["tracks:0"], "prop": "name"},
        ]},
        get_song=lambda: song, get_app=lambda: None,
    )
    r = out["value"]
    assert out["ok"] and r[0] == {"ok": True} and not r[1]["ok"]
    assert r[2] == {"ok": True, "value": "Kick"} and track.mute is True


def test_dispatch_get_song_root():
    song = FakeSong([FakeTrack("Kick")])
    out = lom.dispatch(
        {"cmd": "get", "root": "song", "path": ["tracks:0"], "prop": "name"},
        get_song=lambda: song, get_app=lambda: None,
    )
    assert out == {"ok": True, "value": "Kick"}


def test_dispatch_set():
    track = FakeTrack("Kick")
    song = FakeSong([track])
    out = lom.dispatch(
        {"cmd": "set", "root": "song", "path": ["tracks:0"], "prop": "mute", "value": True},
        get_song=lambda: song, get_app=lambda: None,
    )
    assert out == {"ok": True}
    assert track.mute is True


def test_dispatch_call():
    song = FakeSong([])
    out = lom.dispatch(
        {"cmd": "call", "root": "song", "path": [], "method": "create_scene", "args": [-1]},
        get_song=lambda: song, get_app=lambda: None,
    )
    assert out == {"ok": True, "value": -1}


def test_dispatch_len():
    song = FakeSong([FakeTrack("A"), FakeTrack("B"), FakeTrack("C")])
    out = lom.dispatch(
        {"cmd": "len", "root": "song", "path": ["tracks"]},
        get_song=lambda: song, get_app=lambda: None,
    )
    assert out == {"ok": True, "value": 3}


def test_dispatch_unknown_root():
    out = lom.dispatch(
        {"cmd": "get", "root": "bogus", "path": [], "prop": "x"},
        get_song=lambda: None, get_app=lambda: None,
    )
    assert out["ok"] is False
    assert "root sconosciuto" in out["error"]


def test_dispatch_unknown_action():
    song = FakeSong([])
    out = lom.dispatch({"cmd": "bogus", "root": "song"}, get_song=lambda: song, get_app=lambda: None)
    assert out["ok"] is False
    assert "comando sconosciuto" in out["error"]


def test_dispatch_missing_field_reports_error_not_crash():
    song = FakeSong([FakeTrack("Kick")])
    out = lom.dispatch(
        {"cmd": "get", "root": "song", "path": ["tracks:0"]},  # manca 'prop'
        get_song=lambda: song, get_app=lambda: None,
    )
    assert out["ok"] is False


def test_dispatch_link_sets_resolved_object_not_json_value():
    class View:
        selected_track = None

    track = FakeTrack("Kick")
    song = FakeSong([track])
    song.view = View()
    out = lom.dispatch(
        {"cmd": "link", "root": "song", "path": ["view"], "prop": "selected_track", "value_path": ["tracks:0"]},
        get_song=lambda: song, get_app=lambda: None,
    )
    assert out == {"ok": True}
    assert song.view.selected_track is track


def test_dispatch_call_resolves_lom_ref_args_for_arrangement_view():
    class Clip:
        def __init__(self, name):
            self.name = name

    class Track:
        def __init__(self):
            self.placed = None

        def duplicate_clip_to_arrangement(self, clip, time):
            self.placed = (clip, time)
            return True

    clip = Clip("Kick Loop")
    track = Track()
    song = FakeSong([])
    song.tracks = [track]
    song.clip_holder = clip  # raggiungibile via path ["clip_holder"]

    out = lom.dispatch(
        {
            "cmd": "call", "root": "song", "path": ["tracks:0"],
            "method": "duplicate_clip_to_arrangement",
            "args": [{"__lom_ref__": ["clip_holder"]}, 4.0],
        },
        get_song=lambda: song, get_app=lambda: None,
    )
    assert out == {"ok": True, "value": True}
    assert track.placed == (clip, 4.0)


def test_dispatch_call_tupleizes_nested_lists_for_boost_python_apis():
    """Clip.set_notes (e altre API boost::python) accettano solo tuple, non
    list: dopo un json.loads gli argomenti annidati sono sempre list, quindi
    dispatch() deve convertirle ricorsivamente prima della call()."""
    received = {}

    class Clip:
        def set_notes(self, notes):
            received["notes"] = notes
            received["type"] = type(notes)
            received["item_type"] = type(notes[0]) if notes else None

    song = FakeSong([])
    song.clip_holder = Clip()

    out = lom.dispatch(
        {
            "cmd": "call", "root": "song", "path": ["clip_holder"],
            "method": "set_notes",
            "args": [[[60, 0.0, 0.5, 100, False]]],
        },
        get_song=lambda: song, get_app=lambda: None,
    )
    assert out == {"ok": True, "value": None}
    assert received["type"] is tuple
    assert received["item_type"] is tuple
    assert received["notes"] == ((60, 0.0, 0.5, 100, False),)


def test_dispatch_call_tupleize_preserves_lom_ref_resolution():
    """Le liste vengono tuplizzate, ma un {'__lom_ref__': [...]} resta
    risolto nell'oggetto LOM referenziato (non nella sua rappresentazione)."""
    class Clip:
        def __init__(self, name):
            self.name = name

    class Track:
        def duplicate_clip_to_arrangement(self, clip, time):
            return (clip, time)

    clip = Clip("Kick Loop")
    track = Track()
    song = FakeSong([])
    song.tracks = [track]
    song.clip_holder = clip

    out = lom.dispatch(
        {
            "cmd": "call", "root": "song", "path": ["tracks:0"],
            "method": "duplicate_clip_to_arrangement",
            "args": [{"__lom_ref__": ["clip_holder"]}, 4.0],
        },
        get_song=lambda: song, get_app=lambda: None,
    )
    assert out["ok"] is True
    resolved_clip, time = out["value"]
    assert resolved_clip == {"__lom_object__": True, "class": "Clip", "repr": str(clip)}
    assert time == 4.0


def test_dispatch_app_root():
    app = object()
    out = lom.dispatch(
        {"cmd": "len", "root": "app", "path": []},
        get_song=lambda: None, get_app=lambda: app,
    )
    # object() non ha __len__: deve tornare errore pulito, non sollevare
    assert out["ok"] is False


def test_dispatch_non_serializable_result_becomes_repr():
    class LomObj:
        def __repr__(self):
            return "<Track Kick>"

    class Root:
        def get_obj(self):
            return LomObj()

    out = lom.dispatch(
        {"cmd": "call", "root": "song", "path": [], "method": "get_obj", "args": []},
        get_song=lambda: Root(), get_app=lambda: None,
    )
    assert out["ok"] is True
    assert out["value"]["__lom_object__"] is True
    assert out["value"]["class"] == "LomObj"
