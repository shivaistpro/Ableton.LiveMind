"""Gain-staging in dB VERI (str_for_value, mai la formula 20log(lin/0.85): sbagliata, ha spostato i fader).
python gain_stage.py idx=dB ... [--listen nome]   (dB <= 0; poi cattura 30 s dal beat 240)"""
import os, sys  # noqa: E401
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _paths import OUT, SHOTS, out_path  # noqa: E402,F401
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lom_direct import Lom
import mixer
a = sys.argv[1:]; name = None
if "--listen" in a:
    i = a.index("--listen"); name = a[i+1]; del a[i:i+2]
lom = Lom(timeout=5); res = {}
for kv in a:
    idx, db = kv.split("="); idx = int(idx); db = float(db)
    assert db <= 0.0001, "fader sopra 0 dB rifiutato"
    f = mixer._db_of(lom, idx); v = mixer.value_for_db(db, f)
    lom.set(mixer._vol_path(idx), "value", v); res[idx] = f(lom.get(mixer._vol_path(idx), "value"))
json.dump(res, open(out_path("gain_stage.json"), "w"))
if name:
    import listen; listen.main(30.0, name, 240.0)
