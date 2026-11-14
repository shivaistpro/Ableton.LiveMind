"""I sottogruppi dentro un gruppo brano devono uscire nel gruppo padre, non nel Main.

I gruppi di categoria clonati come sottogruppi hanno ereditato 'AudioOut/Main'
(erano al livello piu' alto): l'audio saltava il bus del brano e EQ/volume del
brano non avevano effetto. Copia l'instradamento di un sottogruppo fatto a mano
(che esce in 'AudioOut/GroupTrack') e cambia solo quello.

Uso: python fix_routing.py <in.als> <out.als> <nome gruppo brano>...
"""
import copy
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from split_by_song import load, save, name_of, pointee_tags  # noqa: E402
from split_v3 import _norm  # noqa: E402


def main(src, dst, songs):
    tree = load(src)
    ls = tree.getroot().find("LiveSet")
    tr = [t for t in ls.find("Tracks") if t.tag != "ReturnTrack"]
    by = {t.get("Id"): t for t in tr}
    ref = next(t for t in tr if t.tag == "GroupTrack" and t.find("TrackGroupId").get("Value") != "-1"
               and t.find("DeviceChain/AudioOutputRouting/Target").get("Value") == "AudioOut/GroupTrack")
    good = ref.find("DeviceChain/AudioOutputRouting")
    fixed = []
    for t in tr:
        g = t.find("TrackGroupId").get("Value")
        if g == "-1" or name_of(by[g]) not in songs:
            continue
        r = t.find("DeviceChain/AudioOutputRouting")
        if r.find("Target").get("Value") == "AudioOut/Main":
            dc = t.find("DeviceChain")
            i = list(dc).index(r)
            dc.remove(r)
            dc.insert(i, copy.deepcopy(good))
            fixed.append(name_of(t))
    save(tree, dst)
    a = load(src).getroot().find("LiveSet")
    b = load(dst).getroot().find("LiveSet")
    pt = pointee_tags(a)
    changed = []
    for x, y in zip(a.find("Tracks"), b.find("Tracks")):
        if ET.tostring(_norm(x, pt)) != ET.tostring(_norm(y, pt)):
            xx, yy = _norm(x, pt), _norm(y, pt)
            for el in (xx, yy):
                dc = el.find("DeviceChain")
                dc.remove(dc.find("AudioOutputRouting"))
            if ET.tostring(xx) != ET.tostring(yy):
                raise SystemExit("ERRORE: cambiato altro oltre l'uscita in %s" % name_of(y))
            changed.append(name_of(y))
    print("uscite corrette (%d): %s" % (len(fixed), fixed))
    print("tracce cambiate solo nell'uscita:", len(changed))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], set(sys.argv[3:]))
