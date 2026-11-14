"""Somma un secondo giro di EQ (misurato DOPO il primo) al primo, in un solo Pro-Q 3 per brano.

Bande alla stessa frequenza (+-6%) e stessa forma si sommano; tetti di sicurezza:
strette (Q>=3) max -5 dB, larghe max -3 dB / +1.5 dB. Il volume e' la somma dei due giri.

Uso: python merge_plans.py <piano1.json> <piano2.json> <out.json>
"""
import json
import sys

NARROW_MIN, BROAD_MIN, BROAD_MAX = -5.0, -3.0, 1.5


def merge(b1, b2):
    out = [dict(b) for b in b1]
    for b in b2:
        same = next((o for o in out if o["shape"] == b["shape"] and (o["q"] >= 3) == (b["q"] >= 3)
                     and abs(o["f"] / b["f"] - 1) <= 0.06), None)
        if same:
            same["g"] = round(same["g"] + b["g"], 1)
        else:
            out.append(dict(b))
    for o in out:
        lo = NARROW_MIN if o["q"] >= 3 else BROAD_MIN
        o["g"] = max(lo, min(BROAD_MAX, o["g"]))
    return [o for o in out if abs(o["g"]) >= 0.3]


def main(p1, p2, dst):
    a = json.load(open(p1, encoding="utf-8-sig"))
    b = json.load(open(p2, encoding="utf-8-sig"))["brani"]
    for song, p in a["brani"].items():
        q = b.get(song, {"bands": [], "gain_db": 0.0})
        p["bands"] = merge(p["bands"], q["bands"])
        p["gain_db"] = round(p["gain_db"] + q["gain_db"], 1)
        assert len(p["bands"]) <= 24
    json.dump(a, open(dst, "w", encoding="utf-8"), indent=1)
    for song, p in a["brani"].items():
        print(song, p["gain_db"], [(b["f"], b["g"], b["q"]) for b in p["bands"]])


if __name__ == "__main__":
    main(*sys.argv[1:4])
