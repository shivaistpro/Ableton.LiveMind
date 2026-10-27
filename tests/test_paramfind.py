from livemind.osc.paramfind import find_param
from livemind.brain.tools import dispatch

NAMES = ["Device On", "Cutoff Freq", "Resonance", "Env Mod", "Decay",
         "Accent Amount", "Drive", "Volume"]


def test_exact():
    assert find_param(NAMES, "Resonance") == 2


def test_substring():
    assert find_param(NAMES, "cutoff") == 1


def test_fuzzy_typo():
    assert find_param(NAMES, "resonanza") == 2   # italiano/typo


def test_case_and_symbols():
    assert find_param(NAMES, "ENV-MOD") == 3


def test_not_found():
    assert find_param(NAMES, "wavetable position") is None


class FakeLive:
    def __init__(self):
        self.calls = []
    def get_device_params(self, t, d):
        return (t, d, *NAMES)
    def get_param_values(self, t, d):
        return (t, d, *[0.5] * len(NAMES))
    def set_device_param(self, t, d, p, v):
        self.calls.append((t, d, p, v))
    def select_track(self, t):
        self.calls.append(("select", t))


def test_dispatch_set_by_name():
    live = FakeLive()
    out = dispatch("set_param_by_name",
                   {"track": 0, "device": 1, "param_name": "drive", "value": 0.7}, live)
    assert "Drive" in out and (0, 1, 6, 0.7) in live.calls


def test_dispatch_params_with_values():
    out = dispatch("get_state", {"what": "device_params", "track": 0, "device": 0}, FakeLive())
    assert "1:Cutoff Freq=0.5" in out


def test_dispatch_load_device_no_loader():
    out = dispatch("load_device", {"track": 0, "device_name": "Serum"}, FakeLive(), loader=None)
    assert "non disponibile" in out


class FakeLoader:
    def load(self, name):
        return f"caricato {name}"


def test_dispatch_load_device_ok():
    live = FakeLive()
    out = dispatch("load_device", {"track": 2, "device_name": "Acid V"}, live, loader=FakeLoader())
    assert "Acid V" in out and ("select", 2) in live.calls
