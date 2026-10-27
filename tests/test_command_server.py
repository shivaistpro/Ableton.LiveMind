"""Test del server TCP thread-safe (remote_script/LiveMind/server.py).

Pura libreria standard: qui simuliamo il 'main thread di Live' con un loop che
chiama drain() a intervalli, esattamente come fara' update_display() dentro
Ableton. Interamente eseguibile fuori da Ableton, con un vero socket locale."""
import importlib.util
import json
import pathlib
import socket
import threading
import time

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[1] / "remote_script" / "LiveMind"


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, _ROOT / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


server_mod = _load("livemind_remote_server", "server.py")


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _run_drain_loop(server, stop_event):
    while not stop_event.is_set():
        server.drain()
        time.sleep(0.01)


def _send_and_recv(port, payload, timeout=5.0):
    with socket.create_connection(("127.0.0.1", port), timeout=timeout) as sock:
        sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))
        sock.settimeout(timeout)
        buf = b""
        while b"\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
    line, _, _ = buf.partition(b"\n")
    return json.loads(line.decode("utf-8"))


@pytest.fixture
def running_server():
    port = _free_port()
    calls = []

    def on_command(cmd):
        calls.append(cmd)
        return {"ok": True, "echo": cmd}

    server = server_mod.CommandServer("127.0.0.1", port, on_command)
    server.start()
    stop_event = threading.Event()
    t = threading.Thread(target=_run_drain_loop, args=(server, stop_event), daemon=True)
    t.start()
    try:
        yield server, port, calls
    finally:
        stop_event.set()
        server.stop()


def test_echo_roundtrip(running_server):
    _server, port, calls = running_server
    reply = _send_and_recv(port, {"cmd": "ping"})
    assert reply == {"ok": True, "echo": {"cmd": "ping"}}
    assert calls == [{"cmd": "ping"}]


def test_multiple_sequential_requests(running_server):
    _server, port, calls = running_server
    for i in range(5):
        reply = _send_and_recv(port, {"cmd": "n", "i": i})
        assert reply["echo"]["i"] == i
    assert len(calls) == 5


def test_invalid_json_returns_error(running_server):
    _server, port, _calls = running_server
    with socket.create_connection(("127.0.0.1", port), timeout=5.0) as sock:
        sock.sendall(b"not json\n")
        sock.settimeout(5.0)
        buf = b""
        while b"\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
    reply = json.loads(buf.partition(b"\n")[0].decode("utf-8"))
    assert reply["ok"] is False
    assert "JSON" in reply["error"]


def test_on_command_exception_is_caught():
    port = _free_port()

    def boom(_cmd):
        raise RuntimeError("kaboom")

    server = server_mod.CommandServer("127.0.0.1", port, boom)
    server.start()
    stop_event = threading.Event()
    t = threading.Thread(target=_run_drain_loop, args=(server, stop_event), daemon=True)
    t.start()
    try:
        reply = _send_and_recv(port, {"cmd": "x"})
        assert reply["ok"] is False
        assert "kaboom" in reply["error"]
    finally:
        stop_event.set()
        server.stop()


def test_timeout_when_drain_never_called():
    port = _free_port()
    server = server_mod.CommandServer("127.0.0.1", port, lambda cmd: {"ok": True})
    server.start()  # nessun drain loop avviato: il comando resta in coda
    try:
        reply = server._submit_and_wait(b'{"cmd":"ping"}', timeout=0.3)
        assert reply["ok"] is False
        assert "timeout" in reply["error"]
    finally:
        server.stop()


def test_concurrent_clients(running_server):
    _server, port, _calls = running_server
    results = []
    lock = threading.Lock()

    def worker(i):
        r = _send_and_recv(port, {"cmd": "w", "i": i})
        with lock:
            results.append(r["echo"]["i"])

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join(timeout=5.0)
    assert sorted(results) == list(range(8))
