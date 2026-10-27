"""Offline tests for the arrangement-analysis tools (no Live, no audio device)."""
import gzip
import json
import math
import os
import struct
import sys

import numpy as np
import pytest

TOOLS = os.path.join(os.path.dirname(__file__), "..", "tools")
sys.path.insert(0, TOOLS)

pytest.importorskip("scipy")
pytest.importorskip("pyloudnorm")


def _write_f32(path, x, sr):
    pcm = np.ascontiguousarray(x, "<f4").tobytes()
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVE")
        f.write(b"fmt " + struct.pack("<IHHIIHH", 16, 3, 2, sr, sr * 8, 8, 32))
        f.write(b"data" + struct.pack("<I", len(pcm)) + pcm)


def test_arr_analyze_trims_and_measures(tmp_path):
    import arr_analyze
    sr = 48000
    t = np.arange(int(12 * sr)) / sr
    tone = 0.5 * np.sin(2 * np.pi * 997 * t)                  # -6.02 dBFS peak
    x = np.stack([tone, tone], 1)
    x = np.concatenate([np.zeros((sr // 2, 2)), x, np.zeros((5 * sr, 2))])  # lead + silent tail
    p = tmp_path / "t.wav"
    _write_f32(str(p), x, sr)
    s, blocks = arr_analyze.main(str(p), 120.0, 0, 2, None, str(tmp_path / "o"))
    assert abs(s["music_end_s"] - 12.0) < 0.1                 # both ends trimmed
    assert abs(s["tp_dbtp"] - (-6.02)) < 0.1                  # true peak of a sine = its peak
    # BS.1770: a 997 Hz stereo sine at -6.02 dBFS peak reads ~ -6.0 LUFS
    assert abs(s["lufs_integrated"] - (-6.0)) < 0.5
    assert s["corr"] > 0.99 and s["side_mid_db"]["mid"] < -60  # dual-mono = pure mid
    assert os.path.exists(str(tmp_path / "o.png"))
    assert all(not b.get("silent") for b in blocks)


def test_float_capture_is_not_clipped(tmp_path):
    """listen.py must keep overs: a +3 dBFS sample has to survive the write."""
    import importlib
    sys.modules.setdefault("soundcard", type(sys)("soundcard"))
    listen = importlib.import_module("listen")
    from stem_report import read_wav
    x = np.array([[1.41, -1.41], [0.0, 0.0]], dtype=np.float32)
    p = str(tmp_path / "over.wav")
    listen.write_wav_f32(p, x, 48000)
    y, sr = read_wav(p)
    assert sr == 48000 and abs(float(y[0, 0]) - 1.41) < 1e-6


def _als(tmp_path):
    xml = """<?xml version="1.0"?><Ableton><LiveSet><Tracks>
<AudioTrack Id="5"><Name><EffectiveName Value="ACID"/></Name><TrackGroupId Value="-1"/>
<DeviceChain><Mixer><Volume><Manual Value="0.5"/></Volume><Pan><Manual Value="0"/></Pan>
<Speaker><Manual Value="true"/></Speaker>
<Sends><TrackSendHolder Id="0"><Send><Manual Value="0.25"/></Send></TrackSendHolder>
<TrackSendHolder Id="1"><Send><Manual Value="0.0003162277571"/></Send></TrackSendHolder></Sends></Mixer>
<DeviceChain><Devices>
<Eq8 Id="1"><On><Manual Value="true"/></On><GlobalGain><Manual Value="0"/></GlobalGain>
<Bands.0><ParameterA><IsOn><Manual Value="true"/></IsOn><Mode><Manual Value="0"/></Mode>
<Freq><Manual Value="120"/></Freq><Gain><Manual Value="0"/></Gain><Q><Manual Value="0.71"/></Q></ParameterA></Bands.0>
<Bands.1><ParameterA><IsOn><Manual Value="true"/></IsOn><Mode><Manual Value="3"/></Mode>
<Freq><Manual Value="190"/></Freq><Gain><Manual Value="11.7"/></Gain><Q><Manual Value="0.28"/></Q></ParameterA></Bands.1>
<Bands.2><ParameterA><IsOn><Manual Value="false"/></IsOn><Mode><Manual Value="3"/></Mode>
<Freq><Manual Value="1000"/></Freq><Gain><Manual Value="5"/></Gain><Q><Manual Value="1"/></Q></ParameterA></Bands.2>
</Eq8>
<PluginDevice Id="2"><On><Manual Value="true"/></On><PluginDesc><Vst3PluginInfo Id="0">
<Preset><Vst3Preset><Name Value=""/></Vst3Preset></Preset><Name Value="Phoscyon 2"/></Vst3PluginInfo></PluginDesc></PluginDevice>
</Devices></DeviceChain></DeviceChain></AudioTrack></Tracks>
<MainTrack><Name><EffectiveName Value="Main"/></Name><DeviceChain><Mixer><Volume><Manual Value="1"/></Volume>
<Pan><Manual Value="0"/></Pan></Mixer><DeviceChain><Devices/></DeviceChain></DeviceChain></MainTrack>
</LiveSet></Ableton>"""
    p = tmp_path / "s.als"
    with gzip.open(p, "wb") as f:
        f.write(xml.encode())
    return str(p)


def test_als_deep_decodes_all_eq_bands_sends_and_vst3_name(tmp_path):
    import als_deep
    r = als_deep.main(_als(tmp_path), str(tmp_path / "d.json"))
    tr = r["tracks"][0]
    assert tr["vol_db"] == round(20 * math.log10(0.5), 1)
    assert tr["sends"] == [{"ret": 0, "db": round(20 * math.log10(0.25), 1)}]  # -inf send skipped
    eq = tr["devices"][0]
    assert eq["bands"] == ["LC48 120Hz Q0.71", "Bell 190Hz +11.7dB Q0.28"]    # off band skipped
    assert tr["devices"][1]["plugin"] == "Phoscyon 2"   # not the empty preset <Name>
