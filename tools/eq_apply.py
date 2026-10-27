"""Carica (se manca) EQ Eight sulla traccia e imposta bande, tutto in un processo.
python eq_apply.py <track> "band:type:x:gain" ...   (x = posizione 0-1, f = 10*2205^x)
type: 0 LC48 1 LC12 2 LowShelf 3 Bell 4 Notch 5 HighShelf 6 HC12 7 HC48  -> out/eq_apply.json"""
import os, sys  # noqa: E401
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _paths import OUT, SHOTS, out_path  # noqa: E402,F401
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lom_direct import Lom
lom = Lom(timeout=10); T = "tracks:%s" % sys.argv[1]; log = {"track": T}
def find():
    n = lom.length([T, "devices"]) or 0
    names = [lom.get([T, "devices:%d" % d], "name") for d in range(n)]
    log.setdefault("devs", []).append(names)
    return next((d for d, nm in enumerate(names) if nm == "EQ Eight"), None)
d = find()
if d is None:
    lom.send({"cmd": "link", "root": "song", "path": ["view"], "prop": "selected_track", "value_path": [T]})
    log["sel"] = lom.send({"cmd": "get", "root": "song", "path": ["view", "selected_track"], "prop": "name"})
    log["load"] = lom.send({"cmd": "call", "root": "app", "path": ["browser"], "method": "load_item",
                            "args": [{"__lom_ref__": ["browser", "audio_effects", "children:17"]}]})
    time.sleep(1.0); d = find()
log["dev"] = d
if d is not None:
    for spec in sys.argv[2:]:
        b, ty, x, g = spec.split(":"); base = 4 + (int(b) - 1) * 10
        for off, v in ((0, 1), (1, float(ty)), (2, float(x)), (3, float(g))):
            p = [T, "devices:%d" % d, "parameters:%d" % (base + off)]
            lom.set(p, "value", v); log[str(lom.get(p, "name"))] = lom.get(p, "value")
json.dump(log, open(out_path("eq_apply.json"), "w"), indent=1, default=str)
