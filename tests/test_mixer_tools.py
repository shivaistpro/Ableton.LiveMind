import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import inject_eq_plan  # noqa: E402
import mixer  # noqa: E402


def live_label(v):
    """Curva finta ma realistica del fader di Live: 0.85 = 0 dB, 1.0 = +6 dB."""
    if v <= 0:
        return "-inf dB"
    return "%.1f dB" % ((v - 0.85) * 40 if v >= 0.4 else -18 + (v - 0.4) * 40 - (0.4 - v) * 100)


def test_parse_db():
    assert mixer.parse_db("-6.0 dB") == -6.0
    assert mixer.parse_db("0.0 dB") == 0.0
    assert mixer.parse_db("-inf dB") == float("-inf")
    assert mixer.parse_db("C3") is None and mixer.parse_db(None) is None


@pytest.mark.parametrize("target", [0.0, -6.0, -12.0])
def test_value_for_db_inverts_live_curve(target):
    v = mixer.value_for_db(target, lambda x: mixer.parse_db(live_label(x)))
    assert mixer.parse_db(live_label(v)) == pytest.approx(target, abs=0.11)


def test_value_for_db_needs_labels():
    with pytest.raises(RuntimeError):
        mixer.value_for_db(-6, lambda x: None)


class FakeLom:
    def __init__(self, names):
        self.names = names
        self.vol = {i: 0.85 for i in list(range(len(names))) + ["M"]}

    def _key(self, path):
        return "M" if path[0] == "master_track" else int(path[0].split(":")[1])

    def length(self, path):
        return len(self.names) if path == ["tracks"] else 0

    def get(self, path, prop):
        if prop == "name":
            return self.names[self._key(path)]
        if prop == "value":
            return self.vol[self._key(path)]
        return False

    def set(self, path, prop, value):
        self.vol[self._key(path)] = value
        return {"ok": True}

    def call(self, path, method, args=None):
        return {"ok": True, "value": live_label(args[0])}


def test_set_gains_by_name_index_master_and_refuse_positive():
    lom = FakeLom(["Kick BUS", "synth", "synth 2"])
    out = mixer.set_gains(lom, {"kick bus": -9, "2": -6, "MASTER": 0, "synth": 3})
    assert out["kick bus"]["db_letto"] == pytest.approx(-9, abs=0.11)
    assert out["2"]["idx"] == 2 and out["MASTER"]["idx"] == "MASTER"
    assert "rifiutato" in out["synth"]["errore"]


def test_resolve_errors():
    with pytest.raises(KeyError):
        mixer.resolve("nessuna", ["a"])
    with pytest.raises(KeyError):
        mixer.resolve("dup", ["dup", "DUP"])
    assert inject_eq_plan.resolve("MASTER", []) == -1
    assert inject_eq_plan.resolve("Bus Kick", ["x", "bus kick"]) == 1


def test_report_flags_solo():
    lom = FakeLom(["a", "b"])
    rows = mixer.report(lom)
    assert [r["nome"] for r in rows] == ["a", "b", "MASTER"]
    assert rows[0]["db"] == 0.0


def test_preset_path(tmp_path):
    p = tmp_path / "BUS KICK.ffp"
    p.write_bytes(b"x")
    assert inject_eq_plan.preset_path("BUS KICK", str(tmp_path)) == str(p)
    with pytest.raises(FileNotFoundError):
        inject_eq_plan.preset_path("manca", str(tmp_path))
