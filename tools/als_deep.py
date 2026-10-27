"""Deep, lossless dump of a set's mix state — what als_scan.py flattens away.

als_scan.py merges every <Manual> of a device into one flat dict, so an EQ
Eight shows ONE of its eight bands and sends are not read at all. This walks
each device keeping the parameter path (Bands.3/ParameterA/Freq), decodes the
EQ Eight into readable bands, and adds sends, automation presence and the
sidechain source of compressors.

Usage: python als_deep.py <set.als> [out.json]
"""
from __future__ import annotations

import gzip
import json
import math
import sys
import xml.etree.ElementTree as ET

EQ8_MODE = {0: "LC48", 1: "LC12", 2: "LShelf", 3: "Bell", 4: "Notch",
            5: "HShelf", 6: "HC12", 7: "HC48"}
SKIP = {"LomId", "LomIdView", "AutomationTarget", "ModulationTarget",
        "MidiControllerRange", "MidiCCOnOffThresholds", "ParameterB",
        "SourceContext", "Pointee", "LastPresetRef", "LockedScripts",
        "BranchSourceContext", "Buffer", "PluginDesc", "ModulationSourceCount"}


def db(v):
    return round(20 * math.log10(v), 1) if v and v > 0 else -120.0


def params(el, prefix=""):
    out = {}
    for ch in el:
        if ch.tag in SKIP:
            continue
        m = ch.find("Manual")
        if m is not None and m.get("Value") is not None:
            out[prefix + ch.tag] = m.get("Value")
        elif len(ch) and ch.tag not in ("Devices", "Branches"):
            out.update(params(ch, prefix + ch.tag + "/"))
    return out


def eq8(p):
    bands = []
    for b in range(8):
        k = "Bands.%d/ParameterA/" % b
        if p.get(k + "IsOn") != "true":
            continue
        mode = EQ8_MODE.get(int(float(p.get(k + "Mode", 3))), "?")
        f = float(p.get(k + "Freq", 0))
        g = float(p.get(k + "Gain", 0))
        q = float(p.get(k + "Q", 0.71))
        s = "%s %.0fHz" % (mode, f)
        if mode in ("LShelf", "Bell", "HShelf"):
            s += " %+.1fdB" % g
        s += " Q%.2f" % q
        bands.append(s)
    return bands


def device(d):
    tag = d.tag
    on = d.find("On/Manual")
    info = {"type": tag, "on": on is None or on.get("Value") == "true"}
    if tag in ("PluginDevice", "AuPluginDevice"):
        # NB: `a or b` on Elements is a bug — an Element with no children is
        # falsy. And VST3 keeps a nested (often empty) <Name> inside its preset,
        # so take the first NON-EMPTY name among the plugin-info's own children.
        nm = None
        for info_el in d.findall("./PluginDesc/*"):
            for tagname in ("PlugName", "Name"):
                el = info_el.find(tagname)
                if el is not None and el.get("Value"):
                    nm = el
                    break
            if nm is not None:
                break
        info["plugin"] = nm.get("Value") if nm is not None else "?"
        return info
    un = d.find("UserName")
    if un is not None and un.get("Value"):
        info["user_name"] = un.get("Value")
    p = params(d)
    if tag == "Eq8":
        info["bands"] = eq8(p)
        info["out_gain"] = p.get("GlobalGain")
    elif tag == "StereoGain":
        info.update({k: p.get(k) for k in ("Gain", "StereoWidth", "MidSideBalance",
                                            "BassMono", "BassMonoFrequency", "Mono", "ChannelMode")})
        try:
            info["gain_db"] = db(float(p.get("Gain")))
        except (TypeError, ValueError):
            pass
    elif tag in ("GlueCompressor", "Compressor2", "Limiter", "DrumBuss", "Reverb",
                 "Delay", "AutoFilter2", "Saturator", "MultibandDynamics"):
        info["p"] = {k: v for k, v in p.items() if "/" not in k or k.startswith("SideChain")}
        sc = d.find(".//SideChain//RoutedInput//Target")
        if sc is not None:
            info["sidechain_src"] = sc.get("Value")
    else:
        info["p"] = {k: v for k, v in list(p.items())[:25]}
    # racks: descend into chains
    chains = d.findall("./Branches/*")
    if chains:
        info["chains"] = []
        for br in chains:
            devs = br.find("./DeviceChain/AudioToAudioDeviceChain/Devices")
            if devs is None:
                devs = br.find("./DeviceChain/MidiToAudioDeviceChain/Devices")
            if devs is None:
                devs = br.find(".//Devices")
            info["chains"].append([device(x) for x in (devs if devs is not None else [])])
    return info


def track(tr):
    name_el = tr.find("Name/EffectiveName")
    mixer = tr.find("DeviceChain/Mixer")
    vol = float(mixer.find("Volume/Manual").get("Value")) if mixer is not None else None
    pan = float(mixer.find("Pan/Manual").get("Value")) if mixer is not None else None
    sends = []
    if mixer is not None:
        for i, h in enumerate(mixer.findall("Sends/TrackSendHolder")):
            v = float(h.find("Send/Manual").get("Value"))
            if v > 0.00032:
                sends.append({"ret": i, "db": db(v)})
    devs = tr.find("DeviceChain/DeviceChain/Devices")
    env = tr.findall("AutomationEnvelopes/Envelopes/AutomationEnvelope")
    speaker = tr.find("DeviceChain/Mixer/Speaker/Manual")
    grp = tr.find("TrackGroupId")
    out = tr.find("DeviceChain/AudioOutputRouting/Target")
    return {"kind": tr.tag, "id": tr.get("Id"),
            "name": name_el.get("Value") if name_el is not None else "?",
            "group_id": grp.get("Value") if grp is not None else None,
            "active": speaker is None or speaker.get("Value") == "true",
            "vol_db": db(vol) if vol is not None else None, "pan": pan,
            "sends": sends, "n_automation": len(env),
            "output": out.get("Value") if out is not None else None,
            "devices": [device(d) for d in (devs if devs is not None else [])]}


def main(path, out=None):
    root = ET.fromstring(gzip.open(path).read())
    ls = root.find("LiveSet")
    res = {"tracks": [track(t) for t in ls.find("Tracks")]}
    main_t = ls.find("MainTrack")
    if main_t is None:
        main_t = ls.find("MasterTrack")
    res["master"] = track(main_t)
    res["returns"] = [t["name"] for t in res["tracks"] if t["kind"] == "ReturnTrack"]
    out = out or path.replace(".als", "_deep.json")
    json.dump(res, open(out, "w"), indent=1)
    print("tracce %d -> %s" % (len(res["tracks"]), out))
    return res


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
