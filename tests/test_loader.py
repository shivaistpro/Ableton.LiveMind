"""Il loader deve ignorare l'eccezione fasulla di pygetwindow (code 0 = successo)
e proseguire fino a Enter, altrimenti il device non si carica mai."""
import types
import livemind.osc.loader as L


class FakeWin:
    def __init__(self):
        self.title = "Ableton Live 12 Suite"
        self.isMinimized = False
    def restore(self): pass
    def minimize(self): pass
    def activate(self):
        raise Exception("Error code from Windows: 0 - Operazione completata.")


def _fake_env(monkeypatch):
    calls = []
    fake_gw = types.SimpleNamespace(getAllWindows=lambda: [FakeWin()])
    fake_pg = types.SimpleNamespace(
        hotkey=lambda *a: calls.append(("hotkey", a)),
        typewrite=lambda *a, **k: calls.append(("typewrite", a)),
        press=lambda *a: calls.append(("press", a)),
    )
    monkeypatch.setattr(L, "_HAS_UI", True, raising=False)
    monkeypatch.setattr(L, "gw", fake_gw, raising=False)
    monkeypatch.setattr(L, "pyautogui", fake_pg, raising=False)
    return calls


def test_focus_live_swallows_activate_error(monkeypatch):
    calls = _fake_env(monkeypatch)
    loader = L.DeviceLoader(search_delay=0.0)
    out = loader.load("Serum 2")
    assert "caricato" in out                      # non ha sollevato / abortito
    assert ("press", ("enter",)) in calls         # e' arrivato fino a Enter
    assert ("press", ("down",)) in calls
