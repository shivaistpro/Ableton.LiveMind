"""Scan a Live set through the LiveMind Remote Script (TCP 127.0.0.1:9005).

Phase 1: find which tracks hold clips in the scene range of interest.
Phase 2: dump details (mixer, devices, routing, clip names) for those tracks only.

Output: JSON on stdout and written to out_path.
"""
from __future__ import annotations
import json
import socket
import sys

HOST, PORT = "127.0.0.1", 9005


class Lom:
    def __init__(self, timeout: float = 10.0):
        self.sock = socket.create_connection((HOST, PORT), timeout=timeout)
        self.buf = b""
        self.timeout = timeout

    def send(self, cmd: dict):
        try:
            self.sock.sendall((json.dumps(cmd) + "\n").encode("utf-8"))
            while b"\n" not in self.buf:
                chunk = self.sock.recv(65536)
                if not chunk:
                    raise ConnectionError("socket closed")
                self.buf += chunk
        except Exception:
            # Reconnect once: the script closes idle connections.
            self.sock = socket.create_connection((HOST, PORT), timeout=self.timeout)
            self.buf = b""
            self.sock.sendall((json.dumps(cmd) + "\n").encode("utf-8"))
            while b"\n" not in self.buf:
                chunk = self.sock.recv(65536)
                if not chunk:
                    raise ConnectionError("socket closed")
                self.buf += chunk
        line, _, self.buf = self.buf.partition(b"\n")
        return json.loads(line.decode("utf-8"))

    def get(self, path, prop, root="song"):
        r = self.send({"cmd": "get", "root": root, "path": path, "prop": prop})
        return r.get("value") if r.get("ok") else None

    def length(self, path, root="song"):
        r = self.send({"cmd": "len", "root": root, "path": path})
        return r.get("value") if r.get("ok") else 0


def main(scene_lo: int, scene_hi: int, out_path: str):
    lom = Lom()
    n_tracks = lom.length(["tracks"])
    n_scenes = lom.length(["scenes"])
    scene_hi = min(scene_hi, n_scenes - 1)

    scenes = {}
    for s in range(scene_lo, scene_hi + 1):
        scenes[s] = lom.get(["scenes:%d" % s], "name")

    active = []
    for t in range(n_tracks):
        hits = []
        for s in range(scene_lo, scene_hi + 1):
            has = lom.get(["tracks:%d" % t, "clip_slots:%d" % s], "has_clip")
            if has:
                hits.append(s)
        if hits:
            active.append((t, hits))

    tracks = []
    for t, hits in active:
        base = ["tracks:%d" % t]
        n_dev = lom.length(base + ["devices"])
        devices = []
        for d in range(n_dev):
            dpath = base + ["devices:%d" % d]
            devices.append({
                "index": d,
                "name": lom.get(dpath, "name"),
                "class_name": lom.get(dpath, "class_name"),
                "is_active": lom.get(dpath, "is_active"),
            })
        clips = {}
        for s in hits:
            cpath = base + ["clip_slots:%d" % s, "clip"]
            clips[s] = {
                "name": lom.get(cpath, "name"),
                "length": lom.get(cpath, "length"),
                "is_audio": lom.get(cpath, "is_audio_clip"),
                "muted": lom.get(cpath, "muted"),
                "gain": lom.get(cpath, "gain") if lom.get(cpath, "is_audio_clip") else None,
            }
        mix = base + ["mixer_device"]
        tracks.append({
            "index": t,
            "name": lom.get(base, "name"),
            "is_midi": lom.get(base, "has_midi_input"),
            "muted": lom.get(base, "mute"),
            "solo": lom.get(base, "solo"),
            "volume": lom.get(mix + ["volume"], "value"),
            "panning": lom.get(mix + ["panning"], "value"),
            "output_type": str(lom.get(base, "current_output_routing")),
            "scenes": hits,
            "devices": devices,
            "clips": clips,
        })

    out = {
        "num_tracks": n_tracks,
        "num_scenes": n_scenes,
        "tempo": lom.get([], "tempo"),
        "scene_range": [scene_lo, scene_hi],
        "scene_names": scenes,
        "active_tracks": tracks,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("scanned %d tracks, %d active in scenes %d-%d -> %s"
          % (n_tracks, len(tracks), scene_lo, scene_hi, out_path))


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3])
