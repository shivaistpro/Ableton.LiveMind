"""Aggiunge sul master un Pro-Q 3 "Club Tilt" (sub + aria per impianti a tromba).

Lo inserisce subito dopo il primo device (Utility con bass mono) e prima del
clipper, cosi' tutti i brani ricevono la stessa correzione e i rapporti tra
brani restano quelli misurati. Non tocca nessuna traccia: lo verifica.

Uso: python master_club.py <in.als> <out.als> [sub_db] [air_db]

Se Club Tilt c'e' gia', ne riscrive solo le bande.
"""
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import als_device as A  # noqa: E402
from proq3 import band, write_ffp  # noqa: E402

FFP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out", "ffp")
TEMPLATE_FFP = os.path.join(FFP_DIR, "Q3_Default Setting.ffp")
NAME = "Club Tilt - Master"


def is_proq3(d):
    b = d.find(".//Buffer") if d.tag == "PluginDevice" else None
    return b is not None and bool(b.text) and "".join(b.text.split())[:8] == "46464253"  # "FFBS"


def main(src, dst, sub_db=1.75, air_db=1.5):
    if os.path.abspath(src) == os.path.abspath(dst):
        raise SystemExit("in e out devono essere file diversi")
    tree = A.load(src)
    root = tree.getroot()
    template = A.find_template(root)
    main_tr = root.find("LiveSet/MainTrack")
    chain = main_tr.find("DeviceChain/DeviceChain/Devices")
    before = len(chain)
    bands = [band(50, "bell", gain=sub_db, q=0.8),          # fondamentale kick/sub
             band(12000, "highshelf", gain=air_db, q=0.7)]  # aria, sopra le trombe 2-4k
    ffp = write_ffp(os.path.join(FFP_DIR, NAME + ".ffp"), bands, template=TEMPLATE_FFP)
    existing = [d for d in chain if d.find("UserName") is not None
                and d.find("UserName").get("Value") == NAME]
    if existing:
        # gia' presente (ritocco): add_proq3 riscrive lo stato del primo Pro-Q 3
        # del master, che deve essere proprio Club Tilt
        first = next(d for d in chain if is_proq3(d))
        assert first is existing[0], "il primo Pro-Q 3 del master non e' Club Tilt"
        A.add_proq3(root, -1, ffp, NAME, template)
        assert len(chain) == before
    else:
        assert not any(is_proq3(d) for d in chain), "c'e' gia' un Pro-Q 3 sul master"
        A.add_proq3(root, -1, ffp, NAME, template)
        assert len(chain) == before + 1
        dev = chain[-1]
        chain.remove(dev)
        chain.insert(1, dev)                   # dopo Utility, prima del clipper
    A.save(tree, dst)
    a = A.load(src).getroot().find("LiveSet/Tracks")
    b = A.load(dst).getroot().find("LiveSet/Tracks")
    same = all(ET.tostring(x) == ET.tostring(y) for x, y in zip(a, b)) and len(a) == len(b)
    print("tracce identiche:", same)
    print("catena master:", [d.tag + ":" + (d.find("UserName").get("Value") or "")
                             for d in A.load(dst).getroot().find(
                                 "LiveSet/MainTrack/DeviceChain/DeviceChain/Devices")])
    if not same:
        raise SystemExit("ERRORE: cambiata una traccia")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], *map(float, sys.argv[3:5]))
