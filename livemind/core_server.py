"""LIVEMIND Core — processo persistente locale, espone un'API HTTP minimale
per il client desktop (livemind_gui). Fa da wrapper a Claude Code CLI in
modalita' headless (`claude -p ... --resume`) cosi' l'LLM gira
sull'abbonamento Claude Pro/Max, non su una API key a consumo. Stato
(sessione, log job) persistito su disco: sopravvive al riavvio del client
GUI e del core stesso — risolve "si perde se riavvio".

Avvio: uvicorn livemind.core_server:app --port 8877
"""
from __future__ import annotations
import json
import os
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / "livemind" / "state"
STATE_FILE = STATE_DIR / "session.json"
JOBS_FILE = STATE_DIR / "jobs.jsonl"
MAX_JOBS_IN_MEMORY = 500
CLAUDE_TURN_TIMEOUT = 600  # sec — un turno puo' costruire molto (tracce/note/device)

app = FastAPI(title="LiveMind Core")

_lock = threading.Lock()
_state = {"session_id": None, "status": "idle", "last_reply": ""}
_jobs: list[dict] = []


def _load_state() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        try:
            _state.update(json.loads(STATE_FILE.read_text(encoding="utf-8")))
            _state["status"] = "idle"  # non si eredita mai uno stato "running" da un crash
        except Exception:
            pass
    if JOBS_FILE.exists():
        try:
            lines = JOBS_FILE.read_text(encoding="utf-8").splitlines()[-MAX_JOBS_IN_MEMORY:]
            for l in lines:
                if not l.strip():
                    continue
                try:
                    parsed = json.loads(l)
                except json.JSONDecodeError:
                    continue  # riga corrotta (scrittura interrotta a meta') — salta, non propagare
                if isinstance(parsed, dict):
                    _jobs.append(parsed)
        except Exception:
            pass


def _save_state() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(_state, ensure_ascii=False), encoding="utf-8")


def _append_job(job: dict) -> None:
    if not isinstance(job, dict):
        return  # difesa: mai scrivere una entry non-dict nel log job
    job["ts"] = datetime.now(timezone.utc).isoformat()
    with _lock:
        _jobs.append(job)
        if len(_jobs) > MAX_JOBS_IN_MEMORY:
            del _jobs[: len(_jobs) - MAX_JOBS_IN_MEMORY]
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(JOBS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(job, ensure_ascii=False) + "\n")


def parse_stream_line(line: str) -> Optional[dict]:
    """Converte una riga di 'claude -p --output-format stream-json' in un
    job normalizzato {type, name, detail, status[, session_id]}. None se la
    riga non contiene nulla di rilevante per la UI (eventi di sistema)."""
    line = line.strip()
    if not line:
        return None
    try:
        ev = json.loads(line)
    except json.JSONDecodeError:
        return None
    t = ev.get("type")
    if t == "assistant":
        out = None
        for block in ev.get("message", {}).get("content", []):
            if block.get("type") == "tool_use":
                out = {"type": "tool_use", "name": block.get("name"),
                       "detail": block.get("input"), "status": "running"}
            elif block.get("type") == "text":
                out = {"type": "text", "name": None,
                       "detail": block.get("text"), "status": "ok"}
        return out
    if t == "user":
        for block in ev.get("message", {}).get("content", []):
            if block.get("type") == "tool_result":
                return {"type": "tool_result", "name": None,
                        "detail": block.get("content"),
                        "status": "error" if block.get("is_error") else "ok"}
    if t == "result":
        return {"type": "result", "name": None, "detail": ev.get("result"),
                "status": "error" if ev.get("is_error") else "ok",
                "session_id": ev.get("session_id")}
    return None


def _run_claude(message: str) -> None:
    """Gira in un thread separato: invoca claude -p, aggiorna stato/job man
    mano che arrivano le righe di stream-json (non solo a fine turno)."""
    with _lock:
        _state["status"] = "running"
        _state["last_reply"] = ""
        session_id = _state.get("session_id")
    cmd = ["claude", "-p", message, "--output-format", "stream-json", "--verbose",
           "--dangerously-skip-permissions"]  # headless: nessuno risponde al prompt di conferma tool, altrimenti pende fino a CLAUDE_TURN_TIMEOUT
    if session_id:
        cmd += ["--resume", session_id]
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)  # forza l'auth OAuth dell'abbonamento, non una API key (magari scaduta) nell'env
    try:
        proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, bufsize=1,
                                 shell=(os.name == "nt"), env=env)  # claude e' .cmd su Windows: CreateProcess non lo lancia senza shell
        for line in proc.stdout:
            job = parse_stream_line(line)
            if not job:
                continue
            _append_job(job)
            if job["type"] == "text":
                with _lock:
                    _state["last_reply"] += job["detail"]
            if job["type"] == "result":
                if job.get("session_id"):
                    with _lock:
                        _state["session_id"] = job["session_id"]
                with _lock:
                    if not _state["last_reply"]:
                        _state["last_reply"] = job["detail"] or ""
        proc.wait(timeout=CLAUDE_TURN_TIMEOUT)
    except FileNotFoundError:
        _append_job({"type": "error", "name": None,
                     "detail": "comando 'claude' non trovato — Claude Code CLI installato e nel PATH?",
                     "status": "error"})
    except Exception as e:
        _append_job({"type": "error", "name": None, "detail": str(e), "status": "error"})
    finally:
        with _lock:
            _state["status"] = "idle"
        _save_state()


class ChatIn(BaseModel):
    message: str


@app.post("/chat")
def chat(body: ChatIn):
    with _lock:
        busy = _state["status"] == "running"
    if busy:
        return {"ok": False, "error": "core occupato, attendi il completamento del turno precedente"}
    threading.Thread(target=_run_claude, args=(body.message,), daemon=True).start()
    return {"ok": True}


@app.get("/status")
def status():
    with _lock:
        return dict(_state)


@app.get("/jobs")
def jobs(since: int = 0):
    with _lock:
        return _jobs[since:]


@app.get("/health")
def health():
    return {"ok": True}


_load_state()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8877)
