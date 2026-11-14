"""Replica lo schema 'un gruppo per brano' per i brani non ancora raggruppati.

I gruppi brano gia' fatti a mano (es. DAJE, PEDALARE...) NON vengono toccati.
Solo le tracce dei gruppi di categoria (synth, drum, kick...) vengono
distribuite: per ogni brano nuovo un gruppo "TRACK n" con sottogruppi
"<categoria> n" clonati dal gruppo di categoria originale (stessi device,
volume e send, quindi stesso suono). Una traccia usata in piu' brani diventa
una copia per brano, ognuna con le sole clip di quel brano. I gruppi di
categoria e le tracce senza clip spariscono.

Uso: python split_cat_groups.py <in.als> <out.als>
"""
from __future__ import annotations

import collections
import sys

from split_by_song import (Ids, Node, build_tree, category, clip_scenes, flatten,
                           keep_only, load, make_group, name_of, pointee_tags, save,
                           clear_arrangement)
import copy
import xml.etree.ElementTree as ET

ORDER = ["kick", "drum", "perc", "synth", "bass/line", "vocal", "vox", "fx"]


def keep_only_scenes(t, keep):
    from split_by_song import slots
    for k, cs in enumerate(slots(t)):
        if k in keep:
            continue
        val = cs.find("ClipSlot/Value")
        if val is not None:
            for ch in list(val):
                val.remove(ch)


def run(src, dst, songs, done_groups):
    tree = load(src)
    ls = tree.getroot().find("LiveSet")
    tracks_el = ls.find("Tracks")
    all_tracks = list(tracks_el)
    returns = [t for t in all_tracks if t.tag == "ReturnTrack"]
    tracks = [t for t in all_tracks if t.tag != "ReturnTrack"]
    ids = Ids(ls, pointee_tags(ls))
    roots, nodes = build_tree(tracks)
    kept = [n for n in roots if n.el.get("Id") in done_groups]
    cats = [n for n in roots if n.el.get("Id") not in done_groups]
    for n in cats:
        if any(k.el.tag == "GroupTrack" for k in n.kids):
            raise SystemExit("gruppo di categoria con sottogruppi: %s" % name_of(n.el))
    new_songs = [s for s in songs if s[0] not in {name_of(n.el) for n in kept}]

    def song_of(sc):
        for lbl, lo, hi in new_songs:
            if lo <= sc <= hi:
                return lbl
        return None

    song_root = {lbl: make_group(ids, cats[0].el, lbl, clean=True) for lbl, _, _ in new_songs}
    sub = {}
    report = collections.defaultdict(list)
    outside, empty = [], []
    for cn in cats:
        cat = category(name_of(cn.el)) or name_of(cn.el)
        for leaf in cn.kids:
            t = leaf.el
            by = collections.defaultdict(list)
            for sc in clip_scenes(t):
                lbl = song_of(sc)
                (outside.append((name_of(t), sc)) if lbl is None else by[lbl].append(sc))
            if not by:
                empty.append(name_of(t))
                continue
            # clip fuori dai brani nuovi (es. scena 0): restano sulla prima copia, suonano come prima
            outside_of = lambda tt, _o=[(sc, None) for sc in clip_scenes(t) if song_of(sc) is None]: _o
            first = True
            pristine = copy.deepcopy(t)
            for lbl, lo, hi in new_songs:
                if lbl not in by:
                    continue
                c = t if first else ids.fresh_copy(pristine)
                if not first:
                    clear_arrangement(c)
                extra = [x for x, _ in outside_of(t)] if first else []
                keep_only_scenes(c, set(by[lbl]) | set(extra))
                first = False
                key = (lbl, cat)
                if key not in sub:
                    num = lbl.split()[-1]
                    sub[key] = make_group(ids, cn.el, "%s %s" % (cat, num), clean=False)
                sub[key].kids.append(Node(c))
                report[lbl].append((cat, name_of(t), by[lbl]))
    for lbl, _, _ in new_songs:
        for cat in ORDER + sorted({c for (l, c) in sub if l == lbl and c not in ORDER}):
            if (lbl, cat) in sub:
                song_root[lbl].kids.append(sub[(lbl, cat)])
    ordered = kept + [song_root[l] for l, _, _ in new_songs]
    new_tracks = flatten(ordered)
    for t in list(tracks_el):
        tracks_el.remove(t)
    for t in new_tracks + returns:
        tracks_el.append(t)
    ids.commit()
    save(tree, dst)
    return report, empty, outside


def verify(src, dst, done_groups):
    import math
    a = load(src).getroot().find("LiveSet")
    b = load(dst).getroot().find("LiveSet")
    ok = True
    ta = [t for t in a.find("Tracks")]
    tb = [t for t in b.find("Tracks")]
    if len(set(t.get("Id") for t in tb)) != len(tb):
        print("ERRORE id traccia duplicati"); ok = False
    pt = pointee_tags(a)
    c = collections.Counter(e.get("Id") for e in b.iter() if e.tag in pt and e.get("Id"))
    if any(v > 1 for v in c.values()):
        print("ERRORE id puntatore duplicati"); ok = False
    byb = {t.get("Id"): t for t in tb}
    pos = {t.get("Id"): i for i, t in enumerate(tb)}
    for i, t in enumerate(tb):
        g = t.find("TrackGroupId").get("Value")
        if g != "-1" and (g not in pos or pos[g] >= i):
            print("ERRORE gruppo", name_of(t)); ok = False

    def cl(ls):
        cc = collections.Counter()
        for t in ls.find("Tracks"):
            for sc in clip_scenes(t):
                cc[(name_of(t), sc)] += 1
        return cc
    if cl(a) != cl(b):
        print("ERRORE clip diverse"); ok = False
    # i gruppi fatti a mano: identici byte per byte
    for gid in done_groups:
        def sub(ts, by):
            out = []
            for t in ts:
                x = t
                while x.find("TrackGroupId").get("Value") != "-1":
                    x = by[x.find("TrackGroupId").get("Value")]
                if x.get("Id") == gid:
                    out.append(ET.tostring(t))
            return out
        bya = {t.get("Id"): t for t in ta}
        if sub(ta, bya) != sub(tb, byb):
            print("ERRORE gruppo fatto a mano modificato:", gid); ok = False

    def path(ls):
        tr = [t for t in ls.find("Tracks") if t.tag != "ReturnTrack"]
        by = {t.get("Id"): t for t in tr}
        out = collections.defaultdict(set)
        for t in tr:
            if t.tag == "GroupTrack":
                continue
            g, gain, devs, x = t.find("TrackGroupId").get("Value"), 0.0, [], t
            chain = [t]
            while g != "-1":
                chain.append(by[g]); g = by[g].find("TrackGroupId").get("Value")
            sends = []
            for x in chain:
                gain += 20 * math.log10(max(float(x.find("DeviceChain/Mixer/Volume/Manual").get("Value")), 1e-9))
                devs += [ET.tostring(d) for d in x.findall("DeviceChain/DeviceChain/Devices/*")]
                sends.append(tuple(s.get("Value") for s in x.findall("DeviceChain/Mixer/Sends/TrackSendHolder/Send/Manual")))
            out[name_of(t)].add((round(gain, 3), len(devs), sends[0]))
        return out
    pa, pb = path(a), path(b)
    diff = [k for k in pb if pb[k] - pa.get(k, set())]
    if diff:
        print("ERRORE percorso audio cambiato:", diff[:10]); ok = False
    print("tracce %d -> %d, clip %d invariate, percorsi audio invariati: %s" % (len(ta), len(tb), sum(cl(a).values()), not diff))
    return ok


if __name__ == "__main__":
    SONGS = [("DAJE", 0, 7), ("PEDALARE", 8, 12), ("SCULETTARE", 13, 20), ("TERRADIMEZZO", 21, 24),
             ("TRACK 5", 25, 31), ("TRACK 6", 32, 37), ("TRACK 7", 38, 42), ("TRACK 8", 43, 46),
             ("TRACK 9", 47, 52), ("TRACK 10", 53, 63), ("TRACK 11", 64, 71)]
    DONE = {"716", "727", "741", "767"}
    rep, empty, outside = run(sys.argv[1], sys.argv[2], SONGS, DONE)
    for lbl, _, _ in SONGS[4:]:
        print("== %s: %d tracce" % (lbl, len(rep[lbl])))
    print("tracce vuote tolte:", empty)
    print("clip fuori dai brani nuovi, rimaste sulla prima copia:", outside)
    sys.exit(0 if verify(sys.argv[1], sys.argv[2], DONE) else 1)
