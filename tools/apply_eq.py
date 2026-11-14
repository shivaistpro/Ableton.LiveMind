"""Mette un Pro-Q 3 (bande statiche da eq_plan.json) e il volume sul gruppo di ogni brano.

Tocca SOLO i gruppi brano indicati: aggiunge un device e cambia il volume.
Verifica che tutte le altre tracce e gruppi restino identici.

Uso: python apply_eq.py <in.als> <out.als> <eq_plan.json>
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import als_device as A  # noqa: E402
from proq3 import band, write_ffp  # noqa: E402
from split_v3 import _norm  # noqa: E402
from split_by_song import pointee_tags, name_of  # noqa: E402
import xml.etree.ElementTree as ET  # noqa: E402

GROUP = {"T5": "TRACK 5", "T6": "TRACK 6", "T7": "TRACK 7", "T8": "TRACK 8",
         "T9": "TRACK 9", "T10": "TRACK 10", "T11": "TRACK 11"}
FFP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out", "ffp")
TEMPLATE_FFP = os.path.join(FFP_DIR, "Q3_Default Setting.ffp")


def main(src, dst, plan_path):
    plan = json.load(open(plan_path, encoding="utf-8-sig"))["brani"]
    tree = A.load(src)
    root = tree.getroot()
    template = A.find_template(root)
    if template is None:
        raise SystemExit("nessun Pro-Q 3 nel set da usare come modello")
    tracks = list(root.find("LiveSet/Tracks"))
    idx = {name_of(t): i for i, t in enumerate(tracks)
           if t.tag == "GroupTrack" and t.find("TrackGroupId").get("Value") == "-1"}
    done = {}
    for song, p in plan.items():
        i = idx[GROUP[song]]
        bands = []
        for b in p["bands"]:
            g = b["g"]
            if b["f"] <= 70 and g < -1.5:
                g = -1.5                         # il sub e' l'identita' della cassa: tagli minimi
            bands.append(band(b["f"], b["shape"], gain=g, q=b["q"]))
        name = "Frozen Beat %s - Bus" % song
        ffp = write_ffp(os.path.join(FFP_DIR, name + ".ffp"), bands, template=TEMPLATE_FFP)
        A.add_proq3(root, i, ffp, name, template)
        A.set_volume(root, i, p["gain_db"])
        done[GROUP[song]] = (len(bands), p["gain_db"])
    A.save(tree, dst)
    # verifica: tutto il resto identico
    a = A.load(src).getroot().find("LiveSet")
    b = A.load(dst).getroot().find("LiveSet")
    pt = pointee_tags(a)
    ta, tb = list(a.find("Tracks")), list(b.find("Tracks"))
    assert len(ta) == len(tb)
    diff = [name_of(x) for x, y in zip(ta, tb)
            if ET.tostring(_norm(x, pt)) != ET.tostring(_norm(y, pt))]
    unexpected = [d for d in diff if d not in done]
    print("gruppi modificati:", done)
    print("tracce cambiate:", diff)
    if unexpected:
        raise SystemExit("ERRORE: cambiate tracce non previste: %s" % unexpected)
    print("OK: cambiati solo i gruppi brano previsti")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
