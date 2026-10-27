"""Imposta una banda di EQ Eight: python eq_set.py <track> <dev> <band> <type> <freqHz> <gainDb> [--listen nome]
type: 0 LC48 1 LC12 2 LowShelf 3 Bell 4 Notch 5 HighShelf 6 HC12 7 HC48"""
import os, sys  # noqa: E401
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _paths import OUT, SHOTS, out_path  # noqa: E402,F401
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lom_direct import Lom
a = sys.argv[1:]; name = None
if "--listen" in a:
    i = a.index("--listen"); name = a[i+1]; del a[i:i+2]
t, d, b, ty, f, g = int(a[0]), int(a[1]), int(a[2]), float(a[3]), float(a[4]), float(a[5])
lom = Lom(timeout=10); P = ["tracks:%d" % t, "devices:%d" % d, "parameters"]
base = 4 + (b - 1) * 10; res = {}
for off, v in ((0, 1), (1, ty), (2, f), (3, g)):
    p = P[:-1] + ["parameters:%d" % (base + off)]
    lom.set(p, "value", v); res[lom.get(p, "name")] = lom.get(p, "value")
json.dump(res, open(out_path("eq_set.json"), "w"), indent=1)
if name:
    import listen; listen.main(30.0, name, 240.0)
