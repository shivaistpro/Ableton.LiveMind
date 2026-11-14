"""Riorganizza un set di Live in un gruppo per brano, offline.

Ogni brano e' un intervallo di scene. Una traccia con clip in piu' brani viene
duplicata: ogni copia tiene solo le clip delle scene del suo brano e finisce
nel gruppo di quel brano, dentro un sottogruppo di categoria (synth, drum,
kick...) che eredita device, mixer e send del gruppo di categoria originale.

Il set di partenza non viene mai toccato: si scrive un .als nuovo.

Gli id di automazione/modulazione devono restare unici in tutto il set: nelle
copie vengono rinumerati da NextPointeeId, e i riferimenti PointeeId interni
alla copia seguono la nuova numerazione.
"""
from __future__ import annotations

import collections
import copy
import gzip
import re
import sys
import xml.etree.ElementTree as ET

CATEGORIES = [("kick", ("kick",)), ("drum", ("drum",)), ("perc", ("perc",)),
              ("bass/line", ("bass", "303")), ("synth", ("synth", "sinth")),
              ("vocal", ("vocal", "voacl")), ("vox", ("vox",)), ("fx", ("fx",))]
SEND_OFF = "0.0003162277571"   # -70 dB: send spento


def load(path):
    with gzip.open(path, "rb") as f:
        return ET.parse(f)


def save(tree, path):
    with gzip.open(path, "wb") as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)


def name_of(t):
    return t.find("Name/EffectiveName").get("Value")


def set_name(t, name):
    for tag in ("EffectiveName", "UserName"):
        el = t.find("Name/" + tag)
        if el is not None:
            el.set("Value", name)


def category(name):
    n = name.lower()
    for cat, keys in CATEGORIES:
        if any(k in n for k in keys):
            return cat
    return None


def slots(t):
    return t.findall("DeviceChain/MainSequencer/ClipSlotList/ClipSlot")


def clip_scenes(t):
    return [k for k, cs in enumerate(slots(t))
            if cs.find("ClipSlot/Value/AudioClip") is not None
            or cs.find("ClipSlot/Value/MidiClip") is not None]


def keep_only(t, lo, hi):
    for k, cs in enumerate(slots(t)):
        if lo <= k <= hi:
            continue
        val = cs.find("ClipSlot/Value")
        if val is not None:
            for ch in list(val):
                val.remove(ch)


def clear_arrangement(t):
    for path in ("DeviceChain/MainSequencer/Sample/ArrangerAutomation/Events",
                 "DeviceChain/MainSequencer/ClipTimeable/ArrangerAutomation/Events"):
        ev = t.find(path)
        if ev is not None:
            for ch in list(ev):
                ev.remove(ch)


def pointee_tags(liveset):
    """Tag i cui Id sono unici in tutto il set e grandi: sono puntatori globali."""
    ids = collections.defaultdict(list)
    for el in liveset.iter():
        v = el.get("Id")
        if v is not None and v.lstrip("-").isdigit():
            ids[el.tag].append(int(v))
    return {t for t, v in ids.items() if len(v) == len(set(v)) and max(v) > 1000}


class Ids:
    def __init__(self, liveset, ptags):
        self.ls = liveset
        self.ptags = ptags
        self.next_p = int(liveset.find("NextPointeeId").get("Value"))
        self.next_t = 1 + max(int(t.get("Id")) for t in liveset.find("Tracks"))

    def fresh_copy(self, el):
        c = copy.deepcopy(el)
        c.set("Id", str(self.next_t))
        self.next_t += 1
        remap = {}
        for e in c.iter():
            if e.tag in self.ptags and e.get("Id") is not None:
                remap[e.get("Id")] = str(self.next_p)
                e.set("Id", str(self.next_p))
                self.next_p += 1
        for e in c.iter("PointeeId"):
            if e.get("Value") in remap:
                e.set("Value", remap[e.get("Value")])
        return c

    def commit(self):
        self.ls.find("NextPointeeId").set("Value", str(self.next_p + 1))


class Node:
    def __init__(self, el):
        self.el, self.kids = el, []


def build_tree(tracks):
    nodes = {t.get("Id"): Node(t) for t in tracks}
    roots = []
    for t in tracks:
        g = t.find("TrackGroupId").get("Value")
        (roots if g == "-1" else nodes[g].kids).append(nodes[t.get("Id")])
    return roots, nodes


def flatten(roots, parent="-1", out=None):
    out = [] if out is None else out
    for n in roots:
        n.el.find("TrackGroupId").set("Value", parent)
        out.append(n.el)
        if n.el.tag == "GroupTrack":
            flatten(n.kids, n.el.get("Id"), out)
    return out


def leaves(node):
    if node.el.tag != "GroupTrack":
        yield node
    for k in node.kids:
        yield from leaves(k)


def ancestors(node_id, parent_of):
    out = []
    while node_id in parent_of:
        node_id = parent_of[node_id]
        out.append(node_id)
    return out


def make_group(ids, template, name, clean):
    g = ids.fresh_copy(template)
    set_name(g, name)
    if clean:
        devs = g.find("DeviceChain/DeviceChain/Devices")
        if devs is not None:
            for d in list(devs):
                devs.remove(d)
        vol = g.find("DeviceChain/Mixer/Volume/Manual")
        if vol is not None:
            vol.set("Value", "1")
        pan = g.find("DeviceChain/Mixer/Pan/Manual")
        if pan is not None:
            pan.set("Value", "0")
        for s in g.findall("DeviceChain/Mixer/Sends/TrackSendHolder/Send/Manual"):
            s.set("Value", SEND_OFF)
    return Node(g)


def run(src, dst, songs, existing):
    """songs: [(label, lo, hi)]; existing: {label: group_id} brani gia' raggruppati."""
    tree = load(src)
    ls = tree.getroot().find("LiveSet")
    tracks_el = ls.find("Tracks")
    all_tracks = list(tracks_el)
    returns = [t for t in all_tracks if t.tag == "ReturnTrack"]
    tracks = [t for t in all_tracks if t.tag != "ReturnTrack"]
    ids = Ids(ls, pointee_tags(ls))
    roots, nodes = build_tree(tracks)
    parent_of = {k.el.get("Id"): n.el.get("Id") for n in nodes.values() for k in n.kids}

    def song_of(scene):
        for i, (_, lo, hi) in enumerate(songs):
            if lo <= scene <= hi:
                return i
        return None

    song_root = {}                       # indice brano -> Node gruppo
    for i, (label, _, _) in enumerate(songs):
        if label in existing:
            song_root[i] = nodes[existing[label]]
    song_ids = {n.el.get("Id"): i for i, n in song_root.items()}
    cat_roots = [n for n in roots if n.el.get("Id") not in song_ids]
    cat_template = {category(name_of(n.el)) or name_of(n.el): n.el for n in cat_roots}
    generic = cat_roots[0].el

    report = collections.defaultdict(list)
    orphan = []                          # clip fuori da ogni brano
    moves = []                           # (song, cat, src_track_el, keep_original)

    for leaf_id, node in list(nodes.items()):
        t = node.el
        if t.tag == "GroupTrack":
            continue
        anc = ancestors(leaf_id, parent_of)
        top = anc[-1] if anc else None
        home = song_ids.get(top)
        sc = clip_scenes(t)
        by_song = collections.defaultdict(list)
        for s in sc:
            k = song_of(s)
            (orphan.append((name_of(t), s)) if k is None else by_song[k].append(s))
        if not by_song:
            continue
        if home is not None and home in by_song:
            keep = home
        elif home is not None:
            keep = None                  # nessuna clip nel suo brano: si sposta
        else:
            keep = min(by_song)
        # categoria: dal gruppo genitore piu' vicino che ne ha una
        cat = None
        for gid in anc:
            cat = category(name_of(nodes[gid].el))
            if cat:
                break
        cat = cat or category(name_of(t)) or (name_of(nodes[top].el) if top else "altro")
        pristine = copy.deepcopy(t)      # le copie partono dalla traccia intatta
        for k in sorted(by_song):
            moves.append((k, cat, t if k == keep else pristine, k == keep))
            report[songs[k][0]].append((name_of(t), by_song[k], k == keep))

    # gruppi dei brani nuovi
    for i, (label, _, _) in enumerate(songs):
        if i not in song_root:
            song_root[i] = make_group(ids, generic, label, clean=True)

    def subgroup(i, cat):
        root = song_root[i]
        for k in root.kids:
            if k.el.tag == "GroupTrack" and category(name_of(k.el)) == cat:
                return k
        tpl = cat_template.get(cat, generic)
        num = re.sub(r"\D", "", songs[i][0]) or songs[i][0]
        g = make_group(ids, tpl, "%s %s" % (cat, num), clean=tpl is generic)
        root.kids.append(g)
        return g

    chain_cache = {}

    def chain_parent(i, src_id, cat):
        """Gruppo che riceve la traccia nel brano i, con la stessa catena di bus
        che la traccia aveva nell'originale, cosi' il suono non cambia."""
        anc = ancestors(src_id, parent_of)          # dal piu' vicino al piu' alto
        top = anc[-1] if anc else None
        if top is None or top not in song_ids:
            if songs[i][0] not in existing:
                return subgroup(i, cat)              # gruppo di categoria clonato
            chain = list(reversed(anc))              # categoria clonata dentro il brano esistente
        else:
            chain = list(reversed(anc))
            if songs[i][0] in existing:
                chain = chain[1:]                    # il bus del brano di arrivo sostituisce quello di partenza
        src_song = name_of(nodes[top].el) if top else "?"
        parent = song_root[i]
        for d in range(len(chain)):
            key = (i, tuple(chain[:d + 1]))
            if key not in chain_cache:
                g = make_group(ids, nodes[chain[d]].el, "%s (da %s)" % (name_of(nodes[chain[d]].el), src_song)
                               if top in song_ids else name_of(nodes[chain[d]].el), clean=False)
                g.el.find("DeviceChain/DeviceChain/Devices")  # device, mixer e send restano quelli originali
                parent.kids.append(g)
                chain_cache[key] = g
            parent = chain_cache[key]
        return parent

    moved_originals = set()
    for i, cat, t, is_orig in moves:
        lo, hi = songs[i][1], songs[i][2]
        if is_orig:
            n = nodes[t.get("Id")]
            keep_only(t, lo, hi)
            if songs_home_is(i, t, song_ids, parent_of):
                continue                 # resta dov'e', nel suo brano
            moved_originals.add(t.get("Id"))
            old = nodes.get(parent_of.get(t.get("Id")))
            if old is not None and n in old.kids:
                old.kids.remove(n)       # via dalla vecchia posizione
            chain_parent(i, t.get("Id"), cat).kids.append(n)
        else:
            c = ids.fresh_copy(t)
            keep_only(c, lo, hi)
            clear_arrangement(c)
            chain_parent(i, t.get("Id"), cat).kids.append(Node(c))

    # togli gli originali spostati e le tracce rimaste senza clip dalle vecchie posizioni
    def prune(node_list):
        out = []
        for n in node_list:
            if n.el.tag == "GroupTrack":
                n.kids = prune(n.kids)
                if not n.kids and n.el.get("Id") not in song_ids and n in cat_roots:
                    continue             # gruppo di categoria svuotato
                out.append(n)
            elif n.el.get("Id") in moved_originals and n not in placed:
                continue
            else:
                out.append(n)
        return out

    placed = set()
    for i in song_root:
        for lf in leaves(song_root[i]):
            if lf.el.get("Id") in moved_originals:
                placed.add(lf)
    # rimuove gli originali spostati dalle categorie (restano solo dove sono stati messi)
    for n in cat_roots:
        n.kids = [k for k in n.kids if k.el.get("Id") not in moved_originals]
    for i in song_root:
        if songs[i][0] in existing:
            continue
    cat_left = prune(cat_roots)
    ordered = [song_root[i] for i in range(len(songs))] + cat_left
    new_tracks = flatten(ordered)
    for t in list(tracks_el):
        tracks_el.remove(t)
    for t in new_tracks + returns:
        tracks_el.append(t)
    ids.commit()
    save(tree, dst)
    return report, orphan


def songs_home_is(i, t, song_ids, parent_of):
    anc = ancestors(t.get("Id"), parent_of)
    return bool(anc) and song_ids.get(anc[-1]) == i


def verify(src, dst, songs):
    a = load(src).getroot().find("LiveSet")
    b = load(dst).getroot().find("LiveSet")
    tb = [t for t in b.find("Tracks") if t.tag != "ReturnTrack"]
    ok = True
    ids = [t.get("Id") for t in b.find("Tracks")]
    if len(ids) != len(set(ids)):
        print("ERRORE: id traccia duplicati"); ok = False
    pt = pointee_tags(a)
    seen = collections.Counter(e.get("Id") for e in b.iter() if e.tag in pt and e.get("Id"))
    dup = [k for k, v in seen.items() if v > 1]
    if dup:
        print("ERRORE: %d id puntatore duplicati" % len(dup)); ok = False
    pos = {t.get("Id"): i for i, t in enumerate(tb)}
    for i, t in enumerate(tb):
        g = t.find("TrackGroupId").get("Value")
        if g != "-1" and (g not in pos or pos[g] >= i):
            print("ERRORE: gruppo non valido per", name_of(t)); ok = False
    nsc = len(b.find("Scenes"))
    for t in tb:
        if t.tag != "GroupTrack" and len(slots(t)) != nsc:
            print("ERRORE: slot", name_of(t)); ok = False

    def clips(ls):
        c = collections.Counter()
        for t in ls.find("Tracks"):
            for s in clip_scenes(t):
                c[(name_of(t), s)] += 1
        return c
    ca, cb = clips(a), clips(b)
    if ca != cb:
        print("ERRORE: clip diverse", (ca - cb).most_common(5), (cb - ca).most_common(5)); ok = False
    # ogni traccia nei gruppi brano ha clip solo nel suo intervallo
    byid = {t.get("Id"): t for t in tb}
    for t in tb:
        if t.tag == "GroupTrack":
            continue
        top = t
        while top.find("TrackGroupId").get("Value") != "-1":
            top = byid[top.find("TrackGroupId").get("Value")]
        lbl = name_of(top)
        rng = [s for s in songs if s[0] == lbl]
        if rng:
            bad = [s for s in clip_scenes(t) if not rng[0][1] <= s <= rng[0][2]]
            if bad:
                print("ERRORE: %s in %s ha clip fuori brano %s" % (name_of(t), lbl, bad)); ok = False
    def paths(ls):
        import math
        tr = [t for t in ls.find("Tracks") if t.tag != "ReturnTrack"]
        by = {t.get("Id"): t for t in tr}
        out = collections.defaultdict(list)
        for t in tr:
            if t.tag == "GroupTrack":
                continue
            g, gain, devs = t.find("TrackGroupId").get("Value"), 0.0, []
            chain = [t]
            while g != "-1":
                chain.append(by[g]); g = by[g].find("TrackGroupId").get("Value")
            for x in chain:
                gain += 20 * math.log10(max(float(x.find("DeviceChain/Mixer/Volume/Manual").get("Value")), 1e-9))
                devs += [d.tag for d in x.findall("DeviceChain/DeviceChain/Devices/*")]
            out[name_of(t)].append((round(gain, 2), tuple(devs), name_of(chain[-1])))
        return out
    pa, pb = paths(a), paths(b)
    changed = []
    for k, v in pb.items():
        for gain, devs, top in v:
            if (gain, devs) != pa[k][0][:2]:
                changed.append((k, pa[k][0][2], top, pa[k][0][0], gain))
    print("percorsi audio diversi dall'originale: %d" % len(changed))
    for c in changed:
        print("   %s: %s -> %s, guadagno %+.2f -> %+.2f dB" % (c[0][:40], c[1], c[2], c[3], c[4]))
    print("tracce %d -> %d, clip %d (invariate: %s)" % (len(a.find("Tracks")), len(b.find("Tracks")), sum(ca.values()), ca == cb))
    return ok


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    SONGS = [("DAJE", 0, 7), ("PEDALARE", 8, 12), ("SCULETTARE", 13, 20),
             ("TERRADIMEZZO", 21, 24), ("TRACK 5", 25, 31), ("TRACK 6", 32, 37),
             ("TRACK 7", 38, 42), ("TRACK 8", 43, 46), ("TRACK 9", 47, 52),
             ("TRACK 10", 53, 63), ("TRACK 11", 64, 71)]
    EXISTING = {"DAJE": "716", "PEDALARE": "727", "SCULETTARE": "741", "TERRADIMEZZO": "767"}
    report, orphan = run(src, dst, SONGS, EXISTING)
    for lbl, _, _ in SONGS:
        rows = report.get(lbl, [])
        print("== %s: %d tracce" % (lbl, len(rows)))
        for nm, sc, orig in rows:
            print("   %s %-40s scene %s" % ("O" if orig else "+", nm[:40], sc))
    if orphan:
        print("CLIP FUORI DA OGNI BRANO:", orphan)
    sys.exit(0 if verify(src, dst, SONGS) else 1)
