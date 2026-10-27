"""Server TCP thread-safe per il Remote Script LiveMind.

Il socket gira su thread separati (uno di accept, uno per client). La Live
Object Model NON e' thread-safe: ogni comando ricevuto viene messo in coda e
resta in attesa finche' il thread principale di Ableton non chiama drain()
(agganciato a update_display(), che Live invoca periodicamente sul main thread).
Questo rispetta il vincolo di CLAUDE.md: mai toccare l'audio/API engine fuori
dal thread giusto.

Pura libreria standard (socket/threading/queue/json): interamente testabile
anche fuori da Ableton, con un vero socket su localhost.
"""
from __future__ import annotations
import json
import queue
import socket
import threading
from typing import Any, Callable, Optional


class CommandServer:
    def __init__(
        self,
        host: str,
        port: int,
        on_command: Callable[[dict], dict],
        log: Callable[[str], None] = lambda *_a: None,
    ) -> None:
        self._host = host
        self._port = port
        self._on_command = on_command  # chiamato SEMPRE dal main thread via drain()
        self._log = log
        self._inbox: "queue.Queue[Callable[[], None]]" = queue.Queue()
        self._sock: Optional[socket.socket] = None
        self._accept_thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self._host, self._port))
        self._sock.listen(4)
        self._sock.settimeout(0.5)
        self._running = True
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()
        self._log(f"LiveMind: in ascolto su {self._host}:{self._port}")

    def stop(self) -> None:
        self._running = False
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass

    def _accept_loop(self) -> None:
        while self._running:
            try:
                conn, _addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._client_loop, args=(conn,), daemon=True).start()

    def _client_loop(self, conn: socket.socket) -> None:
        buf = b""
        with conn:
            conn.settimeout(30)
            while self._running:
                try:
                    chunk = conn.recv(4096)
                except (socket.timeout, OSError):
                    break
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if not line.strip():
                        continue
                    reply = self._submit_and_wait(line)
                    try:
                        conn.sendall((json.dumps(reply) + "\n").encode("utf-8"))
                    except OSError:
                        return

    def _submit_and_wait(self, line: bytes, timeout: float = 10.0) -> dict:
        done = threading.Event()
        box: dict = {}

        def job() -> None:
            box["reply"] = self._process(line)
            done.set()

        self._inbox.put(job)
        if not done.wait(timeout=timeout):
            return {"ok": False, "error": "timeout: il main thread di Live non ha processato il comando"}
        return box.get("reply", {"ok": False, "error": "nessuna risposta prodotta"})

    def _process(self, line: bytes) -> dict:
        try:
            cmd = json.loads(line.decode("utf-8"))
        except Exception as e:
            return {"ok": False, "error": f"JSON non valido: {e}"}
        try:
            return self._on_command(cmd)
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    def drain(self, max_items: int = 50) -> int:
        """Da chiamare dal main thread di Live (tick periodico). Ritorna quanti
        comandi ha eseguito."""
        n = 0
        for _ in range(max_items):
            try:
                job = self._inbox.get_nowait()
            except queue.Empty:
                break
            job()
            n += 1
        return n
