"""Un gruppo per brano per i brani non ancora raggruppati, a suono invariato.

Regole (lezione del 14/11: un gruppo spento fuso con uno acceso ha acceso 3 casse):
- i gruppi brano fatti a mano non si toccano;
- ogni traccia di un gruppo di categoria va nel brano delle sue clip, dentro un
  sottogruppo clonato dal SUO gruppo di categoria (mai fusi due gruppi diversi:
  stato attivo/spento, device, volume e send restano quelli);
- traccia in piu' brani = una copia per brano, ognuna con le sole clip di quel brano;
- il gruppo brano e' neutro: nessun device, 0 dB, pan centro, send spenti, attivo;
- clip fuori da ogni brano nuovo (scena 0) -> gruppo INTRO, stesse regole.
Verifica: ogni traccia nuova e' identica a una dell'originale (stesso nome) tolte
clip, id e gruppo; la catena di gruppi sopra ogni traccia e' identica a quella
originale, togliendo il gruppo brano neutro.

Uso: python split_v3.py <in.als> <out.als>   |   python split_v3.py verify <in> <out>
"""
from __future__ import annotations

import collections
import copy
import sys
import xml.etree.ElementTree as ET

from split_by_song import (Ids, Node, build_tree, clear_arrangement, clip_scenes,
                           flatten, load, make_group, name_of, pointee_tags, save, slots)

ORDER = ["kick", "drum", "perc", "synth", "bass", "vocal", "vox", "fx"]
NEW_SONGS = [("TRACK 5", 25, 31), ("TRACK 6", 32, 37), ("TRACK 7", 38, 42),
             ("TRACK 8", 43, 46), ("TRACK 9", 47, 52), ("TRACK 10", 53, 63),
             ("TRACK 11", 64, 71)]
DONE = {"716", "727", "741", "767"}           # DAJE, PEDALARE, SCULETTARE, TERRADIMEZZO


def keep_scenes(t, keep):
    for k, cs in enumerate(slots(t)):
        if k in keep:
            continue
        val = cs.find("ClipSlot/Value")
        if val is not None:
            for ch in list(val):
                val.remove(ch)


def order_key(name):
    n = name.lower()
    for i, c in enumerate(ORDER):
        if c in n:
            return (i, n)
    return (len(ORDER), n)


def build(src, dst):
    tree = load(src)
    ls = tree.getroot().find("LiveSet")
    tel = ls.find("Tracks")
    allt = list(tel)
    rets = [t for t in allt if t.tag == "ReturnTrack"]
    tracks = [t for t in allt if t.tag != "ReturnTrack"]
    ids = Ids(ls, pointee_tags(ls))
    roots, nodes = build_tree(tracks)
    kept = [n for n in roots if n.el.get("Id") in DONE]
    cats = [n for n in roots if n.el.get("Id") not in DONE]
    for n in cats:
        if n.el.tag != "GroupTrack" or any(k.el.tag == "GroupTrack" for k in n.kids):
            raise SystemExit("struttura inattesa nel gruppo %s" % name_of(n.el))

    def song_of(sc):
        for lbl, lo, hi in NEW_SONGS:
            if lo <= sc <= hi:
                return lbl
        return "INTRO"

    labels = [l for l, _, _ in NEW_SONGS] + ["INTRO"]
    song_root = {l: make_group(ids, cats[0].el, l, clean=True) for l in labels}
    sub = {}                                       # (brano, id gruppo categoria) -> Node
    empty = []
    for cn in cats:
        for leaf in cn.kids:
            t = leaf.el
            by = collections.defaultdict(set)
            for sc in clip_scenes(t):
                by[song_of(sc)].add(sc)
            if not by:
                empty.append(name_of(t))
                continue
            pristine = copy.deepcopy(t)
            first = True
            for lbl in labels:
                if lbl not in by:
                    continue
                c = t if first else ids.fresh_copy(pristine)
                if not first:
                    clear_arrangement(c)
                keep_scenes(c, by[lbl])
                first = False
                key = (lbl, cn.el.get("Id"))
                if key not in sub:
                    suffix = lbl.split()[-1] if lbl != "INTRO" else "intro"
                    sub[key] = make_group(ids, cn.el, "%s %s" % (name_of(cn.el), suffix), clean=False)
                sub[key].kids.append(Node(c))
    for lbl in labels:
        groups = [g for (l, _), g in sub.items() if l == lbl]
        song_root[lbl].kids = sorted(groups, key=lambda g: order_key(name_of(g.el)))
    ordered = kept + [song_root[l] for l in labels if song_root[l].kids]
    new = flatten(ordered)
    for t in list(tel):
        tel.remove(t)
    for t in new + rets:
        tel.append(t)
    ids.commit()
    save(tree, dst)
    neutral = {song_root[l].el.get("Id") for l in labels}
    return empty, neutral


def _norm(el, ptags, drop=("Name",)):
    """Copia senza cio' che non e' suono: id, nomi, appartenenza al gruppo, clip."""
    c = copy.deepcopy(el)
    c.attrib.pop("Id", None)
    for e in c.iter():
        if e.tag in ptags or e.tag in ("VstPreset", "Vst3Preset"):   # Live rinumera i preset al salvataggio
            e.attrib.pop("Id", None)
        if e.tag in ("SelectedDevice", "SelectedEnvelope", "Color"):   # solo vista/colore, non suono
            e.set("Value", "x")
        if e.tag in ("LomId", "LomIdView", "PointeeId", "TrackGroupId", "TakeId"):  # TakeId: Live lo rinumera al salvataggio
            e.set("Value", "x")
    for tag in drop:
        for parent in list(c.iter()):
            for ch in list(parent):
                if ch.tag == tag:
                    parent.remove(ch)
    return c


def _leaf_sig(t, ptags):
    c = _norm(t, ptags, drop=("Name", "MainSequencer", "ViewData", "TrackUnfolded"))
    return ET.tostring(c)


def _group_sig(g, ptags):
    return ET.tostring(_norm(g.find("DeviceChain"), ptags,
                             drop=("Name", "ViewData", "ClipSlotList", "Slots")))


def _clips(ls, ptags):
    c = collections.Counter()
    for t in ls.find("Tracks"):
        for k, cs in enumerate(slots(t)):
            for cl in cs.findall("ClipSlot/Value/*"):
                c[(k, ET.tostring(_norm(cl, ptags, drop=())))] += 1
    return c


def _chains(ls, ptags, skip):
    tr = [t for t in ls.find("Tracks") if t.tag != "ReturnTrack"]
    by = {t.get("Id"): t for t in tr}
    out = collections.defaultdict(list)
    for t in tr:
        if t.tag == "GroupTrack":
            continue
        g, chain = t.find("TrackGroupId").get("Value"), []
        while g != "-1":
            if g not in skip:
                chain.append(_group_sig(by[g], ptags))
            g = by[g].find("TrackGroupId").get("Value")
        out[_leaf_sig(t, ptags)].append(tuple(chain))
    return out


def verify(src, dst, neutral_names=tuple(l for l, _, _ in NEW_SONGS) + ("INTRO",)):
    a = load(src).getroot().find("LiveSet")
    b = load(dst).getroot().find("LiveSet")
    ptags = pointee_tags(a)
    ok = True
    tb = [t for t in b.find("Tracks") if t.tag != "ReturnTrack"]
    neutral = {t.get("Id") for t in tb if t.tag == "GroupTrack"
               and t.find("TrackGroupId").get("Value") == "-1" and name_of(t) in neutral_names}
    for t in tb:
        if t.get("Id") not in neutral:
            continue
        m = t.find("DeviceChain/Mixer")
        devs = t.findall("DeviceChain/DeviceChain/Devices/*")
        neutral_ok = (not devs and float(m.find("Volume/Manual").get("Value")) == 1.0
                      and float(m.find("Pan/Manual").get("Value")) == 0.0
                      and m.find("Speaker/Manual").get("Value") == "true"
                      and all(float(s.get("Value")) < 0.001 for s in m.findall("Sends/TrackSendHolder/Send/Manual")))
        if not neutral_ok:
            print("ERRORE gruppo brano non neutro:", name_of(t)); ok = False
    ids = [t.get("Id") for t in b.find("Tracks")]
    if len(ids) != len(set(ids)):
        print("ERRORE id traccia duplicati"); ok = False
    cnt = collections.Counter(e.get("Id") for e in b.iter() if e.tag in ptags and e.get("Id"))
    if any(v > 1 for v in cnt.values()):
        print("ERRORE id puntatore duplicati"); ok = False
    ca, cb = _clips(a, ptags), _clips(b, ptags)
    if ca != cb:
        print("ERRORE clip diverse: mancano %d, in piu' %d" % (sum((ca - cb).values()), sum((cb - ca).values()))); ok = False
    ch_a, ch_b = _chains(a, ptags, set()), _chains(b, ptags, neutral)
    bad = 0
    for sig, chains in ch_b.items():
        if sig not in ch_a:
            bad += 1
            continue
        for c in chains:
            if c not in ch_a[sig]:
                bad += 1
    if bad:
        print("ERRORE %d tracce con traccia o catena di gruppi diversa dall'originale" % bad); ok = False
    pos = {t.get("Id"): i for i, t in enumerate(tb)}
    for i, t in enumerate(tb):
        g = t.find("TrackGroupId").get("Value")
        if g != "-1" and (g not in pos or pos[g] >= i):
            print("ERRORE gruppo non valido:", name_of(t)); ok = False
    print("tracce %d -> %d | clip %d uguali: %s | tracce e catene identiche: %s"
          % (len(a.find("Tracks")), len(b.find("Tracks")), sum(ca.values()), ca == cb, bad == 0))
    return ok


if __name__ == "__main__":
    if sys.argv[1] == "verify":
        sys.exit(0 if verify(sys.argv[2], sys.argv[3]) else 1)
    empty, neutral = build(sys.argv[1], sys.argv[2])
    print("tracce vuote tolte:", empty)
    sys.exit(0 if verify(sys.argv[1], sys.argv[2]) else 1)


