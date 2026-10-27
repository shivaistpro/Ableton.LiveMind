"""Tutto-in-uno: seleziona la traccia, carica Compressor nativo dal browser,
lo collega in sidechain al bus 'kick' e imposta i parametri di pompaggio.
Un solo processo = meno round trip di bridge rispetto a chiamare piu' script.

Uso: python add_sidechain_full.py <track_idx>
"""
import os, sys  # noqa: E401
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _paths import OUT, SHOTS, out_path  # noqa: E402,F401
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lom_direct import Lom

COMP_PATH = ["browser", "audio_effects", "children:10"]  # "Compressor", trovato una volta


def main(track_idx):
    lom = Lom(timeout=10)
    TRK = "tracks:%d" % track_idx

    lom.send({"cmd": "link", "root": "song", "path": ["view"], "prop": "selected_track",
              "value_path": [TRK]})
    r_load = lom.send({"cmd": "call", "root": "app", "path": ["browser"], "method": "load_item",
                        "args": [{"__lom_ref__": COMP_PATH}]})

    n = lom.send({"cmd": "len", "root": "song", "path": [TRK, "devices"]})
    count = n.get("value", 0) if n.get("ok") else 0
    dev_idx = count - 1
    DEV = [TRK, "devices:%d" % dev_idx]

    devname = lom.send({"cmd": "get", "root": "song", "path": DEV, "prop": "name"})

    n_rt = lom.send({"cmd": "len", "root": "song", "path": DEV + ["available_input_routing_types"]})
    rt_count = n_rt.get("value", 0) if n_rt.get("ok") else 0
    kick_i = None
    for i in range(rt_count):
        r = lom.send({"cmd": "get", "root": "song",
                       "path": DEV + ["available_input_routing_types:%d" % i], "prop": "display_name"})
        if (r.get("value") or "").strip().lower() == "kick":
            kick_i = i
            break

    out = {"track_idx": track_idx, "device_idx": dev_idx, "device_name": devname.get("value"),
           "load_ok": r_load.get("ok"), "n_routing_opts": rt_count, "kick_index": kick_i}

    if devname.get("value") != "Compressor":
        out["error"] = "il device caricato non e' Compressor: " + str(devname)
        _dump(track_idx, out)
        return out
    if kick_i is None:
        out["error"] = "bus 'kick' non trovato fra le opzioni di routing"
        _dump(track_idx, out)
        return out

    r_link = lom.send({"cmd": "link", "root": "song", "path": DEV, "prop": "input_routing_type",
                        "value_path": DEV + ["available_input_routing_types:%d" % kick_i]})
    out["link_ok"] = r_link.get("ok")

    # 1=Threshold 2=Ratio 4=Attack 5=Release 20=S/C On
    sets = {1: 0.55, 2: 0.85, 4: 0.03, 5: 0.30, 20: 1.0}
    out["param_sets"] = {}
    for pidx, val in sets.items():
        r = lom.send({"cmd": "set", "root": "song", "path": DEV + ["parameters:%d" % pidx],
                       "prop": "value", "value": val})
        out["param_sets"][pidx] = r.get("ok")

    _dump(track_idx, out)
    return out


def _dump(track_idx, out):
    path = out_path("sidechain_full_%d.json" % track_idx)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main(int(sys.argv[1]))
