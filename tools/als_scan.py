"""Read an Ableton .als (gzipped XML) offline and dump the mix-relevant structure.

Replaces thousands of LOM round trips with one file read. Reports, for a beat
range, which tracks carry arrangement clips, their full device chain with
parameter values, mixer settings, sends and routing.

Usage: python als_scan.py <set.als> [start_beat] [end_beat] [out.json]
"""
from __future__ import annotations
import gzip
import json
import sys
import xml.etree.ElementTree as ET


def val(node, name, default=None):
    """Read <name Value="..."/> under node."""
    el = node.find(name)
    if el is None:
        return default
    v = el.get("Value")
    return v if v is not None else default


def num(node, name, default=None):
    v = val(node, name)
    if v is None:
        return default
    try:
        return float(v)
    except ValueError:
        return default


def track_name(tr):
    n = tr.find("Name")
    if n is None:
        return None
    return val(n, "EffectiveName") or val(n, "UserName")


def device_params(dev, limit=400):
    """Collect parameter-like children: elements holding a Manual value."""
    out = {}
    for el in dev.iter():
        manual = el.find("Manual")
        if manual is None:
            continue
        v = manual.get("Value")
        if v is None:
            continue
        tag = el.tag
        if tag in out:
            continue
        out[tag] = v
        if len(out) >= limit:
            break
    return out


def scan_devices(tr, with_params):
    devs = []
    chain = tr.find("DeviceChain/DeviceChain/Devices")
    if chain is None:
        return devs
    for i, dev in enumerate(list(chain)):
        entry = {"i": i, "type": dev.tag, "on": val(dev, "On/Manual")}
        un = dev.find("UserName")
        if un is not None and un.get("Value"):
            entry["user_name"] = un.get("Value")
        pn = dev.find("PluginDesc")
        if pn is not None:
            # VST3 stores the name in Vst3PluginInfo/Name, VST2 in VstPluginInfo/PlugName.
            for tag, field in (("Vst3PluginInfo", "Name"), ("VstPluginInfo", "PlugName"),
                               ("AuPluginInfo", "Name")):
                info = pn.find(tag)
                if info is not None:
                    nm = info.find(field)
                    if nm is not None and nm.get("Value"):
                        entry["plugin"] = nm.get("Value")
                        break
        if with_params:
            entry["params"] = device_params(dev)
        devs.append(entry)
    return devs


def arrangement_clips(tr, lo, hi):
    """Only clips on the arrangement timeline.

    Session clips live under ClipSlotList; walking the whole track picks those
    up too and every track looks active. The arrangement timeline is under
    MainSequencer/ClipTimeable/ArrangerAutomation/Events (audio and MIDI alike).
    """
    clips = []
    for events in tr.iter("Events"):
        for clip in list(events):
            if not clip.tag.endswith("Clip"):
                continue
            t = num(clip, "CurrentStart")
            e = num(clip, "CurrentEnd")
            if t is None or e is None:
                continue
            if e <= lo or t >= hi:
                continue
            nm = clip.find("Name")
            clips.append({
                "start": t, "end": e,
                "name": nm.get("Value") if nm is not None else None,
                "kind": clip.tag,
                "disabled": val(clip, "Disabled"),
            })
    clips.sort(key=lambda c: c["start"])
    return clips


def main(path, lo=0.0, hi=1e9, out_path=None, with_params=True):
    with gzip.open(path, "rb") as f:
        root = ET.parse(f).getroot()

    live_set = root.find("LiveSet") or root
    tempo = None
    for el in root.iter("Tempo"):
        tempo = num(el, "Manual")
        if tempo:
            break

    locators = []
    for loc in root.iter("Locator"):
        locators.append({"name": val(loc, "Name"), "time": num(loc, "Time")})

    tracks = []
    for kind in ("AudioTrack", "MidiTrack", "GroupTrack", "ReturnTrack"):
        for tr in live_set.iter(kind):
            clips = arrangement_clips(tr, lo, hi)
            mixer = tr.find("DeviceChain/Mixer")
            entry = {
                "kind": kind,
                "id": tr.get("Id"),
                "name": track_name(tr),
                "group_id": val(tr, "TrackGroupId"),
                "n_clips": len(clips),
                "clips": clips[:40],
                "volume": num(mixer, "Volume/Manual") if mixer is not None else None,
                "pan": num(mixer, "Pan/Manual") if mixer is not None else None,
                "speaker_on": val(tr, "DeviceChain/Mixer/Speaker/Manual"),
                "devices": scan_devices(tr, with_params),
            }
            tracks.append(entry)

    active = [t for t in tracks if t["n_clips"] or t["kind"] in ("ReturnTrack", "GroupTrack")]
    # Live 12 renamed MasterTrack to MainTrack; keep both for older sets.
    master = live_set.find("MainTrack")
    if master is None:
        master = live_set.find("MasterTrack")
    out = {
        "file": path,
        "tempo": tempo,
        "range_beats": [lo, hi],
        "locators": locators,
        "n_tracks_total": len(tracks),
        "n_tracks_active": len([t for t in tracks if t["n_clips"]]),
        "master_devices": scan_devices(master, with_params) if master is not None else [],
        "master_volume": num(master.find("DeviceChain/Mixer"), "Volume/Manual") if master is not None and master.find("DeviceChain/Mixer") is not None else None,
        "tracks": active,
    }
    js = json.dumps(out, indent=1, ensure_ascii=False)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(js)
        print("tempo=%s  tracce=%d  attive nel range=%d  -> %s"
              % (tempo, out["n_tracks_total"], out["n_tracks_active"], out_path))
        print("locatori: " + ", ".join("%s@%s" % (l["name"], l["time"]) for l in locators))
    else:
        print(js)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0],
         float(a[1]) if len(a) > 1 else 0.0,
         float(a[2]) if len(a) > 2 else 1e9,
         a[3] if len(a) > 3 else None)
