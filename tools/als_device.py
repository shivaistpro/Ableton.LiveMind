"""Insert FabFilter Pro-Q 3 instances into a Live set, offline, with a preset baked in.

Live stores a VST3 plugin's state as a hex Buffer inside <PluginDevice>. For
Pro-Q 3 that buffer is:

    b"FFBS" | uint32 version(1) | uint32 count(358) | 358 float32
    b"FQ3p" | uint32 3 | uint32 len(name) | name | ff ff ff ff
            | uint32 1 | uint32 5 | b"Pro-Q" | 00 00 00 00
            | b"CuSV" | uint32 1 | uint32 0

The first 334 floats are byte-identical to a .ffp payload, so a preset written
by proq3.py can be dropped straight into the buffer. That makes the whole job
deterministic: no plugin UI, no clicking, no LOM round trips.

A <PluginDevice> node from an already-loaded instance is used as the template
so every field Live expects is present; only the buffer and the ids change.
"""
from __future__ import annotations

import copy
import gzip
import os
import struct
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from proq3 import read_ffp  # noqa: E402

FFBS_COUNT = 358
FFP_COUNT = 334


def build_buffer(ffp_path: str, preset_name: str = "CIRCUIT") -> bytes:
    """Turn a .ffp into the plugin-state buffer Live stores in the set."""
    _, floats = read_ffp(ffp_path)
    if len(floats) != FFP_COUNT:
        raise ValueError("il .ffp ha %d float, attesi %d" % (len(floats), FFP_COUNT))
    payload = list(floats) + [0.0] * (FFBS_COUNT - FFP_COUNT)

    name = preset_name.encode("ascii", "replace")
    out = b"FFBS" + struct.pack("<II", 1, FFBS_COUNT)
    out += struct.pack("<%df" % FFBS_COUNT, *payload)
    out += b"FQ3p" + struct.pack("<II", 3, len(name)) + name
    out += b"\xff\xff\xff\xff" + struct.pack("<II", 1, 5) + b"Pro-Q" + b"\x00" * 4
    out += b"CuSV" + struct.pack("<II", 1, 0)
    return out


def hexdump(b: bytes, width: int = 32) -> str:
    h = b.hex().upper()
    lines = [h[i:i + width * 2] for i in range(0, len(h), width * 2)]
    return "\n".join("\t\t\t" + ln for ln in lines)


def load(path):
    with gzip.open(path, "rb") as f:
        return ET.parse(f)


def save(tree, path):
    with gzip.open(path, "wb") as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)


def next_id(root) -> int:
    el = root.find("LiveSet/NextPointeeId")
    return int(el.get("Value")) if el is not None else 40000


def bump_id(root, by: int):
    el = root.find("LiveSet/NextPointeeId")
    if el is not None:
        el.set("Value", str(int(el.get("Value")) + by))


def find_template(root):
    """A <PluginDevice> that already holds a Pro-Q 3 state, to clone from."""
    for dev in root.iter("PluginDevice"):
        buf = dev.find(".//Buffer")
        if buf is None or not buf.text:
            continue
        head = "".join(buf.text.split())[:8]
        if bytes.fromhex(head) == b"FFBS":
            return dev
    return None


def renumber(node, base: int) -> int:
    """Give every id-bearing element in a cloned device a fresh number."""
    n = base
    for el in node.iter():
        for attr in ("Id",):
            if attr in el.attrib and el.attrib[attr].isdigit():
                el.set(attr, str(n))
                n += 1
        if el.tag in ("LomId", "PointeeId") and el.get("Value", "0") != "0":
            el.set("Value", str(n))
            n += 1
    return n


def add_proq3(root, track_index: int, ffp_path: str, preset_name: str,
              template) -> None:
    if track_index < 0:
        tr = root.find("LiveSet/MainTrack") or root.find("LiveSet/MasterTrack")
    else:
        tr = list(root.find("LiveSet/Tracks"))[track_index]
    chain = tr.find("DeviceChain/DeviceChain/Devices")
    if chain is None:
        raise ValueError("traccia %d senza catena device" % track_index)

    existing = None
    for d in list(chain):
        if d.tag != "PluginDevice":
            continue
        b = d.find(".//Buffer")
        if b is not None and b.text and bytes.fromhex("".join(b.text.split())[:8]) == b"FFBS":
            existing = d
            break
    if existing is not None:
        # gia' c'e' un Pro-Q 3 su questa traccia: riscrivo il suo stato
        existing.find(".//Buffer").text = (
            "\n" + hexdump(build_buffer(ffp_path, preset_name)) + "\n\t\t\t")
        on = existing.find("On/Manual")
        if on is not None:
            on.set("Value", "true")
        un = existing.find("UserName")
        if un is not None:
            un.set("Value", preset_name)
        return

    dev = copy.deepcopy(template)
    base = next_id(root)
    used = renumber(dev, base)
    bump_id(root, used - base + 1)

    buf = dev.find(".//Buffer")
    buf.text = "\n" + hexdump(build_buffer(ffp_path, preset_name)) + "\n\t\t\t"

    on = dev.find("On/Manual")
    if on is not None:
        on.set("Value", "true")
    un = dev.find("UserName")
    if un is not None:
        un.set("Value", preset_name)

    chain.append(dev)


def set_volume(root, track_index: int, gain_db: float):
    """Set a track's mixer volume. Live stores it linear: 1.0 = 0 dB."""
    import math
    if track_index < 0:
        tr = root.find("LiveSet/MainTrack")
    else:
        tr = list(root.find("LiveSet/Tracks"))[track_index]
    el = tr.find("DeviceChain/Mixer/Volume/Manual")
    if el is None:
        return None
    old = float(el.get("Value"))
    el.set("Value", "%.10f" % (10 ** (gain_db / 20.0)))
    return old


def strip_proq3(root, track_index: int) -> int:
    """Remove every Pro-Q 3 already on a track, so injection starts clean."""
    if track_index < 0:
        tr = root.find("LiveSet/MainTrack")
    else:
        tr = list(root.find("LiveSet/Tracks"))[track_index]
    chain = tr.find("DeviceChain/DeviceChain/Devices")
    if chain is None:
        return 0
    n = 0
    for d in list(chain):
        if d.tag != "PluginDevice":
            continue
        b = d.find(".//Buffer")
        if b is not None and b.text and bytes.fromhex("".join(b.text.split())[:8]) == b"FFBS":
            chain.remove(d)
            n += 1
    return n


def track_name(tr):
    n = tr.find("Name/EffectiveName")
    return n.get("Value") if n is not None else "?"


def main(als_in, als_out, plan):
    tree = load(als_in)
    root = tree.getroot()
    template = find_template(root)
    if template is None:
        raise SystemExit("nessun Pro-Q 3 gia' presente nel set: caricane uno a mano "
                         "una volta sola, salva, e rilancia (serve come modello XML)")
    tracks = list(root.find("LiveSet/Tracks"))
    for idx, (ffp, name) in plan.items():
        strip_proq3(root, idx)
        add_proq3(root, idx, ffp, name, template)
        label = "MASTER" if idx < 0 else track_name(tracks[idx])[:26]
        print("  traccia %-4d %-26s <- %s" % (idx, label, name))
    save(tree, als_out)
    print("scritto:", als_out)


if __name__ == "__main__":
    import json
    plan = {int(k): tuple(v) for k, v in json.load(open(sys.argv[3], encoding="utf-8")).items()}
    main(sys.argv[1], sys.argv[2], plan)
