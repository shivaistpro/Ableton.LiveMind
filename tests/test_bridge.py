import json
import time
from livemind.bridge import parse_new_lines, BridgeServer


def test_parse_valid_and_garbage():
    text = '{"id":"1","tool":"transport","args":{"action":"play"}}\nGARBAGE\n\n{"tool":"fire","args":{"what":"scene","index":0}}'
    cmds = parse_new_lines(text)
    assert len(cmds) == 2
    assert cmds[0]["id"] == "1"
    assert cmds[1]["id"] is None and cmds[1]["tool"] == "fire"


def test_parse_missing_tool_skipped():
    assert parse_new_lines('{"id":"x","args":{}}') == []


class FakeLive:
    def __init__(self): self.calls = []
    def __getattr__(self, name):
        def rec(*a, **k): self.calls.append((name, a))
        return rec


def test_bridge_end_to_end(tmp_path):
    live = FakeLive()
    b = BridgeServer(str(tmp_path), live, poll_s=0.05, say=lambda *a: None)
    b.start()
    time.sleep(0.2)  # il server registra l'offset iniziale
    with open(tmp_path / "inbox.jsonl", "a") as f:
        f.write(json.dumps({"id": "c1", "tool": "transport",
                            "args": {"action": "set_tempo", "bpm": 150}}) + "\n")
    deadline = time.time() + 3
    result = None
    while time.time() < deadline:
        out = tmp_path / "outbox.jsonl"
        if out.exists() and out.read_text().strip():
            result = json.loads(out.read_text().strip().splitlines()[-1])
            break
        time.sleep(0.05)
    b.stop()
    assert result is not None and result["id"] == "c1" and "ok" in result["result"]
    assert ("set_tempo", (150,)) in live.calls


def test_bridge_dedup(tmp_path):
    live = FakeLive()
    b = BridgeServer(str(tmp_path), live, poll_s=0.05, say=lambda *a: None)
    b.start()
    time.sleep(0.2)
    line = json.dumps({"id": "dup", "tool": "transport", "args": {"action": "play"}}) + "\n"
    with open(tmp_path / "inbox.jsonl", "a") as f:
        f.write(line + line)
    time.sleep(0.5)
    b.stop()
    assert live.calls.count(("play", ())) == 1


def test_bridge_per_id_reply_file(tmp_path):
    """Readback a prova di mount: ogni risposta genera reply.<id>.json fresco."""
    live = FakeLive()
    b = BridgeServer(str(tmp_path), live, poll_s=0.05, say=lambda *a: None)
    b.start()
    time.sleep(0.2)
    with open(tmp_path / "inbox.jsonl", "a") as f:
        f.write(json.dumps({"id": "rb1", "tool": "transport",
                            "args": {"action": "play"}}) + "\n")
    deadline = time.time() + 3
    rf = tmp_path / "reply.rb1.json"
    while time.time() < deadline and not rf.exists():
        time.sleep(0.05)
    b.stop()
    assert rf.exists()
    obj = json.loads(rf.read_text())
    assert obj["id"] == "rb1"


def test_write_voice_transcript(tmp_path):
    """La voce in modalita BRIDGE scrive un file nuovo per-frase, leggibile fresco."""
    from livemind.bridge import write_voice_transcript
    p = write_voice_transcript(str(tmp_path), "metti il cutoff a meta", ts_ms=123)
    import os
    assert os.path.basename(p) == "voice.123.txt"
    assert open(p, encoding="utf-8").read() == "metti il cutoff a meta"
