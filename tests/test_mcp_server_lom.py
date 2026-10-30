"""Test del layer MCP basato LOM (livemind/mcp_server_lom.py). build_tools() e'
pura Python: nessuna rete, nessun pacchetto 'mcp' richiesto (import di FastMCP
isolato in create_server, mai chiamato qui). FakeLomClient replica l'interfaccia
di LomClient senza aprire un vero socket."""
from livemind.mcp_server_lom import build_tools


class FakeLomClient:
    def __init__(self):
        self.calls = []

    def ping(self):
        self.calls.append(("ping", (), {}))
        return {"ok": True, "pong": True}

    def get(self, path, prop, root="song"):
        self.calls.append(("get", (path, prop), {"root": root}))
        return {"ok": True, "value": "Kick"}

    def set(self, path, prop, value, root="song"):
        self.calls.append(("set", (path, prop, value), {"root": root}))
        return {"ok": True}

    def call(self, path, method, args=None, root="song"):
        self.calls.append(("call", (path, method, args), {"root": root}))
        return {"ok": True, "value": 42}

    def length(self, path, root="song"):
        self.calls.append(("length", (path,), {"root": root}))
        return {"ok": True, "value": 3}


def test_build_tools_exposes_all_expected_names():
    tools = build_tools(FakeLomClient())
    assert set(tools.keys()) == {
        "connection_status", "lom_get", "lom_set", "lom_call", "lom_len", "lom_notes",
        "sample_load", "dsp_render",
    }


def test_connection_status_ok():
    client = FakeLomClient()
    tools = build_tools(client)
    out = tools["connection_status"]()
    assert "connesso" in out
    assert ("ping", (), {}) in client.calls


def test_connection_status_error():
    class DeadClient(FakeLomClient):
        def ping(self):
            return {"ok": False, "error": "connection refused"}

    tools = build_tools(DeadClient())
    out = tools["connection_status"]()
    assert "NON risponde" in out
    assert "connection refused" in out


def test_lom_get_forwards_path_and_prop():
    client = FakeLomClient()
    tools = build_tools(client)
    out = tools["lom_get"](path=["tracks:0"], prop="name")
    assert out == "Kick"
    assert ("get", (["tracks:0"], "name"), {"root": "song"}) in client.calls


def test_lom_get_error_is_readable():
    class ErrClient(FakeLomClient):
        def get(self, path, prop, root="song"):
            return {"ok": False, "error": "boom"}

    tools = build_tools(ErrClient())
    out = tools["lom_get"](path=[], prop="x")
    assert out.startswith("ERRORE")
    assert "boom" in out


def test_lom_set_forwards_value():
    client = FakeLomClient()
    tools = build_tools(client)
    out = tools["lom_set"](path=["tracks:0"], prop="mute", value=True)
    assert out == "ok"
    assert ("set", (["tracks:0"], "mute", True), {"root": "song"}) in client.calls


def test_lom_call_forwards_args_and_root():
    client = FakeLomClient()
    tools = build_tools(client)
    out = tools["lom_call"](path=["tracks:0"], method="rename", args=["Kick Hard"], root="song")
    assert out == "42"
    assert ("call", (["tracks:0"], "rename", ["Kick Hard"]), {"root": "song"}) in client.calls


def test_lom_call_app_root_for_browser():
    client = FakeLomClient()
    tools = build_tools(client)
    tools["lom_call"](path=["browser"], method="load_item", args=[], root="app")
    assert ("call", (["browser"], "load_item", []), {"root": "app"}) in client.calls


def test_lom_len():
    client = FakeLomClient()
    tools = build_tools(client)
    out = tools["lom_len"](path=["tracks"])
    assert out == "3"


def test_lom_notes_get_extended_uses_legacy_get_notes():
    """get_notes_extended ritorna un MidiNoteVector opaco non
    serializzabile; get_notes (API legacy) ritorna direttamente tuple
    JSON-friendly e resta funzionante in questa build della LOM."""
    class NotesClient(FakeLomClient):
        def call(self, path, method, args=None, root="song"):
            self.calls.append(("call", (path, method, args), {"root": root}))
            return {"ok": True, "value": [[36, 0.0, 0.25, 127, False]]}

    client = NotesClient()
    tools = build_tools(client)
    out = tools["lom_notes"](action="get_extended", path=["tracks:0", "clip_slots:0", "clip"])
    name, args, _kw = client.calls[-1]
    assert name == "call"
    assert args[1] == "get_notes"
    assert out == str([{"pitch": 36, "start_time": 0.0, "duration": 0.25, "velocity": 127, "mute": False}])


def test_lom_notes_add_merges_with_existing_via_legacy_set_notes():
    """add_new_notes non e' utilizzabile in questa build della LOM: rifiuta
    sia dict che tuple per TNoteSpecification ("No registered converter ...
    from this Python object of type dict/tuple/str" a seconda
    dell'incapsulamento) — bug verificato in Live, non reintrodurre.
    'add' quindi legge le note esistenti con get_notes, le unisce a quelle
    nuove e riscrive tutto con set_notes (l'unica API verificata
    funzionante)."""
    class NotesClient(FakeLomClient):
        def call(self, path, method, args=None, root="song"):
            self.calls.append(("call", (path, method, args), {"root": root}))
            if method == "get_notes":
                return {"ok": True, "value": [[36, 0.0, 0.25, 127, False]]}
            return {"ok": True, "value": None}

    client = NotesClient()
    tools = build_tools(client)
    new_note = {"pitch": 40, "start_time": 1.0, "duration": 0.25, "velocity": 100, "mute": False}
    tools["lom_notes"](action="add", path=["p"], notes=[new_note])
    calls = [c for c in client.calls if c[0] == "call"]
    assert calls[-2][1][1] == "get_notes"
    assert calls[-1][1][1] == "set_notes"
    assert calls[-1][1][2] == [[[36, 0.0, 0.25, 127, False], [40, 1.0, 0.25, 100, False]]]


def test_lom_notes_set_extended_overwrites_via_legacy_set_notes():
    client = FakeLomClient()
    tools = build_tools(client)
    notes = [{"pitch": 36, "start_time": 0.0, "duration": 0.25, "velocity": 127, "mute": False}]
    tools["lom_notes"](action="set_extended", path=["p"], notes=notes)
    name, args, _kw = client.calls[-1]
    assert name == "call"
    assert args[1] == "set_notes"
    assert args[2] == [[[36, 0.0, 0.25, 127, False]]]


def test_lom_notes_remove_clears_via_legacy_set_notes():
    client = FakeLomClient()
    tools = build_tools(client)
    tools["lom_notes"](action="remove", path=["p"])
    name, args, _kw = client.calls[-1]
    assert args[1] == "set_notes"
    assert args[2] == [[]]


def test_lom_notes_add_stops_if_get_notes_fails():
    class ErrClient(FakeLomClient):
        def call(self, path, method, args=None, root="song"):
            self.calls.append(("call", (path, method, args), {"root": root}))
            if method == "get_notes":
                return {"ok": False, "error": "no clip"}
            return {"ok": True, "value": None}

    client = ErrClient()
    tools = build_tools(client)
    out = tools["lom_notes"](action="add", path=["p"], notes=[])
    assert out.startswith("ERRORE")
    assert not any(c[0] == "call" and c[1][1] == "set_notes" for c in client.calls)


def test_lom_notes_unknown_action():
    tools = build_tools(FakeLomClient())
    out = tools["lom_notes"](action="bogus", path=[])
    assert "sconosciuta" in out


def test_lom_notes_error_forwarded():
    class ErrClient(FakeLomClient):
        def call(self, path, method, args=None, root="song"):
            return {"ok": False, "error": "no clip"}

    tools = build_tools(ErrClient())
    out = tools["lom_notes"](action="get_extended", path=["p"])
    assert out.startswith("ERRORE")
    assert "no clip" in out


def test_lom_set_value_schema_has_explicit_types():
    """Regressione: 'value' senza un tipo esplicito in JSON-Schema (era Any
    nudo) fa si' che il client MCP lo serializzi come stringa grezza invece
    che come number/bool — setattr() sulla LOM fallisce poi con
    ArgumentError perche' la C++ API si aspetta un float/bool nativo."""
    from mcp.server.fastmcp.tools.base import Tool
    from livemind.mcp_server_lom import build_tools as _bt

    tools = _bt(FakeLomClient())
    t = Tool.from_function(tools["lom_set"], name="lom_set")
    value_schema = t.parameters["properties"]["value"]
    branch_types = {branch.get("type") for branch in value_schema.get("anyOf", [])}
    assert {"boolean", "integer", "number", "string"} <= branch_types
