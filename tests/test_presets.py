import struct
import pytest
from livemind.presets import kick3, smoothop

# ---------- KICK 3 (XML) ----------
XML = ('<?xml version="1.0"?>\n<Kick3><PARAMS>'
       '<PARAM id="Slot1Type" value="1.0"/>'
       '<PARAM id="Slot1PitchSemi" value="0.0"/>'
       '<PARAM id="Slot2Type" value="2.0"/>'
       '<PARAM id="Slot2PitchSemi" value="0.5"/>'
       '<PARAM id="Slot3Type" value="0.0"/>'
       '<PARAM id="masterLength" value="700.0"/>'
       '</PARAMS><DATA slot1_File="Clicks/Drive.wav" slot2_File="////////"/></Kick3>')


def test_kick3_get_set():
    assert kick3.get_param(XML, "masterLength") == "700.0"
    x = kick3.set_param(XML, "masterLength", 420)
    assert kick3.get_param(x, "masterLength") == "420"
    assert kick3.get_param(XML, "masterLength") == "700.0"  # originale intatto


def test_kick3_active_slots():
    assert kick3.active_slots(XML) == [1, 2]  # Type != 0


def test_kick3_clear_sample():
    x = kick3.clear_sample(XML, 1)
    assert 'slot1_File="////////"' in x and "Drive.wav" not in x


def test_kick3_transpose():
    x = kick3.transpose_semi(XML, -0.62)
    assert kick3.get_param(x, "Slot1PitchSemi") == "-0.62"
    assert kick3.get_param(x, "Slot2PitchSemi") == "-0.12"  # 0.5 - 0.62


# ---------- Smooth Operator (.baby binario) ----------
def _make_baby(name, value):
    return (b"HEADER" + b"PARAM\x00\x01\x02id\x00\x01\x08\x05" + name.encode()
            + b"\x00value\x00\x01\x09\x04" + struct.pack("<d", value) + b"\x00")


def test_smoothop_get():
    d = _make_baby("attack", 25.0)
    assert abs(smoothop.get_param(d, "attack") - 25.0) < 1e-9
    assert smoothop.get_param(d, "missing") is None


def test_smoothop_set_roundtrip():
    d = _make_baby("threshold", -16.0)
    d2 = smoothop.set_param(d, "threshold", -12.0)
    assert abs(smoothop.get_param(d2, "threshold") + 12.0) < 1e-9
    assert len(d2) == len(d)  # dimensione invariata


def test_smoothop_params_dict():
    d = _make_baby("focus", 78.0)
    assert "focus" in smoothop.params(d)


# ---------- Serum 2 (header + JSON + zstd(CBOR)) ----------
serum2 = pytest.importorskip("livemind.presets.serum2")


def _have_deps():
    try:
        import zstandard, cbor2  # noqa
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _have_deps(), reason="zstandard/cbor2 non installati")
def test_serum2_roundtrip():
    hdr = {"fileType": "SerumPreset", "presetName": "TEST", "product": "Serum2"}
    flag = 2
    obj = {"Global0": {"plainParams": {"kParamMasterVolume": 0.5}},
           "Oscillator0": {"plainParams": {"kParamVolume": 1.0}}}
    raw = serum2.dumps(hdr, flag, obj)
    assert raw[:8] == b"XferJson"
    h2, f2, o2 = serum2.loads(raw)
    assert h2["presetName"] == "TEST" and f2 == 2
    assert o2["Global0"]["plainParams"]["kParamMasterVolume"] == 0.5


@pytest.mark.skipif(not _have_deps(), reason="zstandard/cbor2 non installati")
def test_serum2_helpers():
    obj = {}
    serum2.enable_osc(obj, serum2.OSC_A, True, 0.8)
    serum2.mono(obj, True)
    serum2.master(obj, 0.2)
    assert serum2.get_param(obj, serum2.OSC_A, "kParamVolume") == 0.8
    assert serum2.get_param(obj, "Global0", "kParamMonoToggle") == 1.0
