"""Test del core server: parsing stream-json e ciclo stato/job — subprocess
'claude' mockato, nessuna rete, nessun Live/Ableton necessario."""
import json
import time

from fastapi.testclient import TestClient

from livemind import core_server as cs


def test_parse_stream_line_tool_use():
    line = json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "lom", "input": {"action": "ping"}}]}})
    job = cs.parse_stream_line(line)
    assert job == {"type": "tool_use", "name": "lom",
                    "detail": {"action": "ping"}, "status": "running"}


def test_parse_stream_line_text():
    line = json.dumps({"type": "assistant", "message": {"content": [
        {"type": "text", "text": "fatto"}]}})
    job = cs.parse_stream_line(line)
    assert job["type"] == "text" and job["detail"] == "fatto"


def test_parse_stream_line_tool_result_error():
    line = json.dumps({"type": "user", "message": {"content": [
        {"type": "tool_result", "content": "boom", "is_error": True}]}})
    job = cs.parse_stream_line(line)
    assert job["status"] == "error" and job["detail"] == "boom"


def test_parse_stream_line_result_carries_session_id():
    line = json.dumps({"type": "result", "result": "ciao", "is_error": False,
                        "session_id": "abc-123"})
    job = cs.parse_stream_line(line)
    assert job == {"type": "result", "name": None, "detail": "ciao",
                    "status": "ok", "session_id": "abc-123"}


def test_parse_stream_line_garbage_returns_none():
    assert cs.parse_stream_line("") is None
    assert cs.parse_stream_line("non e' json") is None
    assert cs.parse_stream_line(json.dumps({"type": "system"})) is None


class FakeProc:
    """Simula subprocess.Popen per claude -p --output-format stream-json."""
    def __init__(self, lines):
        self.stdout = iter(lines)
        self.stderr = None

    def wait(self, timeout=None):
        return 0


def test_run_claude_updates_state_and_jobs(monkeypatch, tmp_path):
    monkeypatch.setattr(cs, "STATE_DIR", tmp_path)
    monkeypatch.setattr(cs, "STATE_FILE", tmp_path / "session.json")
    monkeypatch.setattr(cs, "JOBS_FILE", tmp_path / "jobs.jsonl")
    cs._jobs.clear()
    cs._state.update({"session_id": None, "status": "idle", "last_reply": ""})

    lines = [
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "lom", "input": {"action": "ping"}}]}}) + "\n",
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "traccia creata"}]}}) + "\n",
        json.dumps({"type": "result", "result": "traccia creata",
                    "is_error": False, "session_id": "sess-1"}) + "\n",
    ]

    def fake_popen(cmd, **kwargs):
        assert cmd[0] == "claude" and cmd[1] == "-p"
        return FakeProc(lines)

    monkeypatch.setattr(cs.subprocess, "Popen", fake_popen)
    cs._run_claude("crea una traccia")

    assert cs._state["status"] == "idle"
    assert cs._state["session_id"] == "sess-1"
    assert cs._state["last_reply"] == "traccia creata"
    assert len(cs._jobs) == 3
    assert (tmp_path / "session.json").exists()


def test_run_claude_missing_binary_reports_error(monkeypatch, tmp_path):
    monkeypatch.setattr(cs, "STATE_DIR", tmp_path)
    monkeypatch.setattr(cs, "STATE_FILE", tmp_path / "session.json")
    monkeypatch.setattr(cs, "JOBS_FILE", tmp_path / "jobs.jsonl")
    cs._jobs.clear()
    cs._state.update({"session_id": None, "status": "idle", "last_reply": ""})

    def fake_popen(cmd, **kwargs):
        raise FileNotFoundError("claude")

    monkeypatch.setattr(cs.subprocess, "Popen", fake_popen)
    cs._run_claude("ciao")

    assert cs._state["status"] == "idle"
    assert any(j["type"] == "error" for j in cs._jobs)


def test_append_job_ignores_non_dict():
    cs._jobs.clear()
    cs._append_job("questa non e' una entry valida")
    assert cs._jobs == []


def test_load_state_skips_corrupt_and_non_dict_lines(monkeypatch, tmp_path):
    monkeypatch.setattr(cs, "STATE_DIR", tmp_path)
    monkeypatch.setattr(cs, "STATE_FILE", tmp_path / "session.json")
    jobs_file = tmp_path / "jobs.jsonl"
    jobs_file.write_text(
        '{"type": "text", "detail": "ok", "status": "ok"}\n'
        '"stringa nuda, non un job"\n'
        'questo non e nemmeno json valido\n'
        '{"type": "result", "detail": "fine", "status": "ok"}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cs, "JOBS_FILE", jobs_file)
    cs._jobs.clear()
    cs._state.update({"session_id": None, "status": "idle", "last_reply": ""})
    cs._load_state()
    assert len(cs._jobs) == 2
    assert all(isinstance(j, dict) for j in cs._jobs)


def test_endpoints_chat_status_jobs(monkeypatch, tmp_path):
    monkeypatch.setattr(cs, "STATE_DIR", tmp_path)
    monkeypatch.setattr(cs, "STATE_FILE", tmp_path / "session.json")
    monkeypatch.setattr(cs, "JOBS_FILE", tmp_path / "jobs.jsonl")
    cs._jobs.clear()
    cs._state.update({"session_id": None, "status": "idle", "last_reply": ""})

    # thread finto, esecuzione sincrona: evita race condition nel test
    class FakeThread:
        def __init__(self, target, args=(), daemon=None):
            self._target, self._args = target, args
        def start(self):
            self._target(*self._args)

    monkeypatch.setattr(cs.threading, "Thread", FakeThread)
    monkeypatch.setattr(cs.subprocess, "Popen",
                         lambda cmd, **kw: FakeProc([json.dumps(
                             {"type": "result", "result": "ok", "is_error": False,
                              "session_id": "s1"}) + "\n"]))

    client = TestClient(cs.app)
    r = client.post("/chat", json={"message": "ciao"})
    assert r.json()["ok"] is True

    r = client.get("/status")
    assert r.json()["status"] == "idle"
    assert r.json()["session_id"] == "s1"

    r = client.get("/jobs")
    assert len(r.json()) == 1

    assert client.get("/health").json() == {"ok": True}
