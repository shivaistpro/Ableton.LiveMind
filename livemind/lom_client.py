"""Client TCP sincrono verso il Remote Script LiveMind (remote_script/LiveMind).

Alternativa diretta-LOM al client OSC (osc/client.py): parla con Ableton via
socket invece che via AbletonOSC, quindi copre anche cio' che l'address space
OSC non espone (rack chain, automation envelope su clip, browser, freeze/flatten
se disponibile nella LOM) tramite path generico get/set/call.
"""
from __future__ import annotations
import json
import socket
from typing import Any, Optional


def ref(path: list) -> dict:
    """Sentinel per un argomento di call() che dev'essere un oggetto LOM
    (non un valore JSON), es. LomClient.call(track_path, "duplicate_clip_to_arrangement",
    [ref(clip_path), 4.0]) — mette un clip di session in Arrangement View."""
    return {"__lom_ref__": path}


class LomClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 9005, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    def _send(self, cmd: dict) -> dict:
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                sock.sendall((json.dumps(cmd) + "\n").encode("utf-8"))
                buf = b""
                sock.settimeout(self.timeout)
                while b"\n" not in buf:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            return {"ok": False, "error": f"LiveMind Remote Script non raggiungibile su {self.host}:{self.port} ({e})"}
        line, _, _ = buf.partition(b"\n")
        if not line:
            return {"ok": False, "error": "nessuna risposta dal Remote Script"}
        try:
            return json.loads(line.decode("utf-8"))
        except Exception as e:
            return {"ok": False, "error": f"risposta non valida: {e}"}

    def ping(self) -> dict:
        return self._send({"cmd": "ping"})

    def get(self, path: Optional[list], prop: str, root: str = "song") -> dict:
        return self._send({"cmd": "get", "root": root, "path": path or [], "prop": prop})

    def set(self, path: Optional[list], prop: str, value: Any, root: str = "song") -> dict:
        return self._send({"cmd": "set", "root": root, "path": path or [], "prop": prop, "value": value})

    def call(self, path: Optional[list], method: str, args: Optional[list] = None, root: str = "song") -> dict:
        return self._send({"cmd": "call", "root": root, "path": path or [], "method": method, "args": args})

    def length(self, path: Optional[list], root: str = "song") -> dict:
        return self._send({"cmd": "len", "root": root, "path": path or []})

    def link(self, path: Optional[list], prop: str, value_path: Optional[list], root: str = "song") -> dict:
        """Come set(), ma il valore e' un altro oggetto LOM risolto da value_path
        (es. Song.view.selected_track = tracks[i] — non passabile via JSON)."""
        return self._send({"cmd": "link", "root": root, "path": path or [], "prop": prop, "value_path": value_path or []})
