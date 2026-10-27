"""Talk to the LiveMind Remote Script directly, bypassing the file bridge.

The bridge is a single synchronous queue: while a `run` command is working,
nothing else gets through, and polling it during a render starved Live badly
enough to hang it. Anything that has to act *while* something long is running
must not go through the bridge — it opens its own socket to 127.0.0.1:9005.

Also usable as a health check: `python lom_direct.py ping`.
"""
from __future__ import annotations

import json
import socket
import sys

HOST, PORT = "127.0.0.1", 9005


class Lom:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def send(self, cmd: dict) -> dict:
        try:
            with socket.create_connection((HOST, PORT), timeout=self.timeout) as s:
                s.sendall((json.dumps(cmd) + "\n").encode("utf-8"))
                buf = b""
                while b"\n" not in buf:
                    chunk = s.recv(65536)
                    if not chunk:
                        break
                    buf += chunk
        except Exception as e:
            return {"ok": False, "error": "Remote Script irraggiungibile: %s" % e}
        line = buf.split(b"\n")[0]
        if not line:
            return {"ok": False, "error": "nessuna risposta"}
        return json.loads(line.decode("utf-8"))

    def ping(self):
        return self.send({"cmd": "ping"})

    def get(self, path, prop, root="song"):
        r = self.send({"cmd": "get", "root": root, "path": path, "prop": prop})
        return r.get("value") if r.get("ok") else None

    def set(self, path, prop, value, root="song"):
        return self.send({"cmd": "set", "root": root, "path": path,
                          "prop": prop, "value": value})

    def call(self, path, method, args=None, root="song"):
        return self.send({"cmd": "call", "root": root, "path": path,
                          "method": method, "args": args})

    def length(self, path, root="song"):
        r = self.send({"cmd": "len", "root": root, "path": path})
        return r.get("value") if r.get("ok") else 0


def set_loop(lom: Lom, start: float, length: float) -> bool:
    """Set the arrangement loop and verify it took — the export dialog
    pre-fills from the loop, and a stale loop silently renders the wrong bars."""
    lom.set([], "loop_start", start)
    lom.set([], "loop_length", length)
    lom.set([], "loop", True)
    got_s = lom.get([], "loop_start")
    got_l = lom.get([], "loop_length")
    # `got or -1` sarebbe un bug: loop_start vale 0.0, che in Python e' falsy.
    got_s = -1.0 if got_s is None else float(got_s)
    got_l = -1.0 if got_l is None else float(got_l)
    ok = abs(got_s - start) < 0.01 and abs(got_l - length) < 0.01
    print("loop: start=%s length=%s  %s" % (got_s, got_l, "OK" if ok else "NON APPLICATO"))
    return ok


if __name__ == "__main__":
    lom = Lom()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ping"
    if cmd == "ping":
        print(json.dumps(lom.ping()))
    elif cmd == "loop":
        set_loop(lom, float(sys.argv[2]), float(sys.argv[3]))
    elif cmd == "get":
        print(lom.get(json.loads(sys.argv[2]), sys.argv[3]))
    else:
        raise SystemExit("comandi: ping | loop <start> <length> | get <path_json> <prop>")
