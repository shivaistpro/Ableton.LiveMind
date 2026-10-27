"""Bridge su file: permette a un brain esterno (un agente IA in sandbox, es. Claude o ChatGPT)
di comandare Live scrivendo JSON nella cartella condivisa.

Protocollo (JSON Lines):
  bridge/inbox.jsonl   <- comandi:  {"id": "...", "tool": "...", "args": {...}}
  bridge/outbox.jsonl  -> risposte: {"id": "...", "result": "..."}

Il server parte dalla fine del file (non riesegue comandi vecchi) e
deduplica per id. Usa lo stesso dispatch dei tool del brain API.
"""
from __future__ import annotations
import json
import os
import threading
import time

from livemind.brain.tools import dispatch


def parse_new_lines(text: str) -> list[dict]:
    """Parsa righe JSONL ignorando righe vuote o corrotte. Puro, testabile."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "tool" in obj:
            obj.setdefault("id", None)
            obj.setdefault("args", {})
            out.append(obj)
    return out


class BridgeServer(threading.Thread):
    def __init__(self, base_dir: str, live, analyzer=None, loader=None,
                 poll_s: float = 0.25, say=print, lom=None):
        super().__init__(daemon=True)
        self.dir = base_dir
        self.inbox = os.path.join(base_dir, "inbox.jsonl")
        self.outbox = os.path.join(base_dir, "outbox.jsonl")
        self.live, self.analyzer, self.loader = live, analyzer, loader
        self.lom = lom
        self.poll_s = poll_s
        self.say = say
        self._stop = threading.Event()
        self._seen: set[str] = set()

    def _reply(self, cmd_id, result: str):
        line = json.dumps({"id": cmd_id, "result": result}, ensure_ascii=False)
        with open(self.outbox, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        # readback a prova di mount: file NUOVO per-id (nuovo inode -> lettura non cache-ata)
        if cmd_id is not None:
            try:
                fn = os.path.join(self.dir, f"reply.{cmd_id}.json")
                with open(fn, "w", encoding="utf-8") as f:
                    f.write(line)
            except Exception:
                pass
        # canale secondario: risposta a terminale
        self.say(f"[bridge] -> {result}")

    def run(self):
        os.makedirs(self.dir, exist_ok=True)
        open(self.inbox, "a").close()
        # Niente offset: il file viene riscritto interamente dal brain esterno, quindi
        # un offset byte si disallinea. Rileggo tutto e deduplico per id (i comandi
        # gia' presenti all'avvio sono marcati visti, cosi' non vengono rieseguiti).
        def _read_cmds() -> list[dict]:
            with open(self.inbox, encoding="utf-8", errors="replace") as f:
                return parse_new_lines(f.read())

        for cmd in _read_cmds():
            if cmd.get("id") is not None:
                self._seen.add(cmd["id"])
        last_mtime = 0.0
        self.say(f"[bridge] attivo su {self.dir}")
        while not self._stop.is_set():
            try:
                mtime = os.path.getmtime(self.inbox)
                if mtime != last_mtime:
                    last_mtime = mtime
                    for cmd in _read_cmds():
                        cid = cmd.get("id")
                        if cid is not None and cid in self._seen:
                            continue
                        if cid is not None:
                            self._seen.add(cid)
                        self.say(f"[bridge] {cmd['tool']} {cmd['args']}")
                        # isolamento per comando: un tool che esplode non deve
                        # far saltare i comandi successivi dello stesso batch
                        try:
                            result = dispatch(cmd["tool"], cmd["args"],
                                              self.live, self.analyzer, self.loader,
                                              lom=self.lom)
                        except Exception as e:
                            result = f"ERRORE {cmd['tool']}: {e!r}"
                        self._reply(cid, result)
            except Exception as e:
                self.say(f"[bridge] errore: {e}")
            time.sleep(self.poll_s)

    def stop(self):
        self._stop.set()


def write_voice_transcript(base_dir: str, text: str, ts_ms=None) -> str:
    """Modalita BRIDGE: la voce non ha un brain locale. Scrive la trascrizione in
    un file NUOVO per-frase (voice.<ts>.txt) -> nuovo inode -> l agente lo
    legge fresco nonostante la cache del mount. Ritorna il path scritto."""
    os.makedirs(base_dir, exist_ok=True)
    ts = ts_ms if ts_ms is not None else int(time.time() * 1000)
    fn = os.path.join(base_dir, f"voice.{ts}.txt")
    with open(fn, "w", encoding="utf-8") as f:
        f.write(text)
    return fn
