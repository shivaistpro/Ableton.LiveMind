"""Scan arrangement clips in a beat range, via the LiveMind Remote Script (TCP 9005).

One query per track to find which tracks have arrangement clips, then details
only for the clips that overlap the range. Keeps the query count low: a full
per-track-per-scene sweep is far too slow on a 300+ track set.
"""
from __future__ import annotations
import json
import socket
import sys

HOST, PORT = "127.0.0.1", 9005


class Lom:
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self.sock = socket.create_connection((HOST, PORT), timeout=timeout)
        self.buf = b""

    def _raw(self, cmd: dict):
        self.sock.sendall((json.dumps(cmd) + "\n").encode("utf-8"))
        while b"\n" not in self.buf:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("closed")
            self.buf += chunk
        line, _, self.buf = self.buf.partition(b"\n")
        return json.loads(line.decode("utf-8"))

    def send(self, cmd: dict):
        try:
            return self._raw(cmd)
        except Exception:
            self.sock = socket.create_connection((HOST, PORT), timeout=self.timeout)
            self.buf = b""
            return self._raw(cmd)

    def get(self, path, prop, root="song"):
        r = self.send({"cmd": "get", "root": root, "path": path, "prop": prop})
        return r.get("value") if r.get("ok") else None

    def length(self, path, root="song"):
        r = self.send({"cmd": "len", "root": root, "path": path})
        return r.get("value") if r.get("ok") else 0


def main(lo: float, hi: float, out_path: str):
    lom = Lom()
    n = lom.length(["tracks"])
    tracks = []
    for t in range(n):
        base = ["tracks:%d" % t]
        n_clips = lom.length(base + ["arrangement_clips"])
        if not n_clips:
            continue
        clips = []
        for c in range(n_clips):
            cp = base + ["arrangement_clips:%d" % c]
            start = lom.get(cp, "start_time")
            end = lom.get(cp, "end_time")
            if start is None or end is None:
                continue
            if end <= lo or start >= hi:
                continue
            clips.append({
                "i": c, "start": start, "end": end,
                "name": lom.get(cp, "name"),
                "is_audio": lom.get(cp, "is_audio_clip"),
                "muted": lom.get(cp, "muted"),
            })
        if not clips:
            continue
        mix = base + ["mixer_device"]
        tracks.append({
            "index": t,
            "name": lom.get(base, "name"),
            "is_midi": lom.get(base, "has_midi_input"),
            "mute": lom.get(base, "mute"),
            "solo": lom.get(base, "solo"),
            "volume": lom.get(mix + ["volume"], "value"),
            "pan": lom.get(mix + ["panning"], "value"),
            "n_devices": lom.length(base + ["devices"]),
            "clips": clips,
        })
        print("t%-4d %-28s %d clip" % (t, str(lom.get(base, "name"))[:28], len(clips)))

    out = {"num_tracks": n, "tempo": lom.get([], "tempo"),
           "range_beats": [lo, hi], "tracks": tracks}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("OK: %d tracce attive nel range -> %s" % (len(tracks), out_path))


if __name__ == "__main__":
    main(float(sys.argv[1]), float(sys.argv[2]), sys.argv[3])
