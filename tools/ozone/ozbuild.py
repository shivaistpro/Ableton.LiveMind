"""Costruisce lo stato completo di Ozone 11 (catena + parametri) a partire dallo stato di default.
comp = u32 magic 0x00688ade | u32 ver 4 | u32 len_zlib | u32 len_json | zlib(JSON)."""
import os
import json, zlib, struct, base64, copy, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _paths import OZONE_VST3, master_src  # noqa: E402
import ozstate

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oz_state_default.bin")

def load_base():
    outer, comp = ozstate.unpack(open(BASE, "rb").read())
    magic, ver, lz, lj = struct.unpack("<4I", comp[:16])
    return outer, comp[:8], json.loads(zlib.decompress(comp[16:]))

def chain_bytes(names):
    return b"".join(b"\0" + struct.pack("<I", len(n)) + n.encode() for n in names)

def build(chain, params):
    """chain: lista nomi modulo (es. 'Equalizer'); params: {elemento: {ParamID: valore}}"""
    outer, head, js = load_base()
    el = js["DSP State"]["Value"]["DSP Elements"]["Value"]
    el["ElementChain"]["Value"]["Extra Bytes"] = {"Type": "Base64", "Value": base64.b64encode(chain_bytes(chain)).decode()}
    for name, pp in params.items():
        d = el[name]["Value"]
        for k, v in pp.items():
            if k not in d:
                raise KeyError(f"{name}: parametro sconosciuto '{k}'")
            t = d[k]["Type"]
            d[k]["Value"] = bool(v) if t == "Bool" else int(v) if t == "UInt" else float(v)
    raw = (json.dumps(js, indent=3, separators=(",", " : ")) + "\n").encode()
    z = zlib.compress(raw, 9)
    comp = head + struct.pack("<2I", len(z) + 4, len(raw)) + z
    return ozstate.pack(outer, comp), comp

if __name__ == "__main__":
    st, comp = build(["Maximizer"], {"Maximizer": {"Gain": 6, "Margin": -1}})
    o2, c2 = ozstate.unpack(st); assert c2 == comp
    print("ok", len(st))
