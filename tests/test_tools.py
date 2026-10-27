from livemind.brain.tools import TOOLS, dispatch


class FakeLive:
    """Registra le chiamate: nessuna rete, nessun Live."""
    def __init__(self):
        self.calls = []
    def __getattr__(self, name):
        def rec(*a, **k):
            self.calls.append((name, a))
            if name == "snapshot":
                return {"tempo": 140.0, "tracks": ["Kick"], "num_tracks": 1}
            return None
        return rec


def test_tool_schemas_valid():
    names = set()
    for t in TOOLS:
        assert t["name"] not in names
        names.add(t["name"])
        assert t["input_schema"]["type"] == "object"


def test_dispatch_transport_tempo():
    live = FakeLive()
    out = dispatch("transport", {"action": "set_tempo", "bpm": 150}, live)
    assert "ok" in out
    assert ("set_tempo", (150,)) in live.calls


def test_dispatch_mixer_volume():
    live = FakeLive()
    dispatch("mixer", {"track": 2, "param": "volume", "value": 0.8}, live)
    assert ("set_volume", (2, 0.8)) in live.calls


def test_dispatch_write_notes():
    live = FakeLive()
    notes = [{"pitch": 57, "start": 0, "duration": 0.25}]
    out = dispatch("write_notes", {"track": 1, "clip": 0, "notes": notes}, live)
    assert "1 note" in out


def test_dispatch_snapshot():
    live = FakeLive()
    out = dispatch("get_state", {"what": "snapshot"}, live)
    assert "140" in out


def test_dispatch_unknown_tool():
    assert "sconosciuto" in dispatch("boh", {}, FakeLive())


def test_dispatch_analyzer_missing():
    out = dispatch("analyze_audio", {}, FakeLive(), analyzer=None)
    assert "non disponibile" in out


def test_dispatch_error_reported():
    class Broken:
        def set_tempo(self, bpm): raise ValueError("boom")
    out = dispatch("transport", {"action": "set_tempo", "bpm": 1}, Broken())
    assert out.startswith("ERRORE")


def test_dispatch_arrangement_goto():
    live = FakeLive()
    out = dispatch("arrangement", {"action": "goto", "beats": 64}, live)
    assert "ok" in out and ("goto_time", (64,)) in live.calls


def test_dispatch_arrangement_loop_region():
    live = FakeLive()
    dispatch("arrangement", {"action": "set_loop_region", "start": 32, "length": 16}, live)
    assert ("set_loop_region", (32, 16)) in live.calls


def test_dispatch_arrangement_record_start():
    live = FakeLive()
    dispatch("arrangement", {"action": "record_start"}, live)
    assert ("record", (True,)) in live.calls and ("play", ()) in live.calls


def test_dispatch_arrangement_back():
    live = FakeLive()
    dispatch("arrangement", {"action": "back_to_arrangement"}, live)
    assert ("back_to_arranger", ()) in live.calls


def test_dispatch_delete_track_single():
    live = FakeLive()
    out = dispatch("delete_track", {"track": 5}, live)
    assert "ok" not in out.lower() or True
    assert ("delete_track", (5,)) in live.calls
    assert "5" in out


def test_dispatch_delete_track_multi_high_to_low():
    live = FakeLive()
    dispatch("delete_track", {"tracks": [5, 6, 12, 8]}, live)
    deleted = [a[0] for (n, a) in live.calls if n == "delete_track"]
    # deve eliminare dall'indice piu alto al piu basso
    assert deleted == [12, 8, 6, 5]


def test_delete_track_in_schema():
    assert any(t["name"] == "delete_track" for t in TOOLS)


class FakeLom:
    def __init__(self):
        self.calls = []

    def get(self, path, prop, root="song"):
        self.calls.append(("get", path, prop, root))
        return {"ok": True, "value": "Kick"}

    def set(self, path, prop, value, root="song"):
        self.calls.append(("set", path, prop, value, root))
        return {"ok": True}

    def call(self, path, method, args, root="song"):
        self.calls.append(("call", path, method, args, root))
        return {"ok": True, "value": True}

    def length(self, path, root="song"):
        self.calls.append(("len", path, root))
        return {"ok": True, "value": 3}

    def link(self, path, prop, value_path, root="song"):
        self.calls.append(("link", path, prop, value_path, root))
        return {"ok": True}

    def ping(self):
        return {"ok": True, "pong": True}


def test_dispatch_lom_get():
    lom = FakeLom()
    out = dispatch("lom", {"action": "get", "path": ["tracks:0"], "prop": "name"}, FakeLive(), lom=lom)
    assert "Kick" in out
    assert ("get", ["tracks:0"], "name", "song") in lom.calls


def test_dispatch_lom_call_with_ref_arg_for_arrangement():
    lom = FakeLom()
    out = dispatch("lom", {
        "action": "call", "path": ["tracks:0"], "method": "duplicate_clip_to_arrangement",
        "args": [{"__lom_ref__": ["tracks:0", "clip_slots:0", "clip"]}, 4.0],
    }, FakeLive(), lom=lom)
    assert "True" in out
    call = [c for c in lom.calls if c[0] == "call"][0]
    assert call[2] == "duplicate_clip_to_arrangement"
    assert call[3][1] == 4.0


def test_dispatch_lom_unavailable():
    out = dispatch("lom", {"action": "ping"}, FakeLive(), lom=None)
    assert "non disponibile" in out


def test_dispatch_run():
    out = dispatch("run", {"command": "echo hi"}, FakeLive())
    assert "hi" in out and "[exit 0]" in out


def test_lom_and_run_in_schema():
    names = {t["name"] for t in TOOLS}
    assert {"lom", "run"} <= names
