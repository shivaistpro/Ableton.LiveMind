"""AbletonOSC client: request/response su UDP (porte 11000/11001)."""
from __future__ import annotations
import threading
import queue
from typing import Any, Optional

try:
    from pythonosc.udp_client import SimpleUDPClient
    from pythonosc.dispatcher import Dispatcher
    from pythonosc.osc_server import ThreadingOSCUDPServer
    _HAS_OSC = True
except ImportError:  # pragma: no cover
    _HAS_OSC = False


class AbletonOSCClient:
    """Client sincrono verso AbletonOSC. Thread-safe per invii semplici."""

    def __init__(self, host: str = "127.0.0.1", send_port: int = 11000,
                 receive_port: int = 11001, timeout: float = 2.0):
        if not _HAS_OSC:
            raise RuntimeError("python-osc non installato: pip install python-osc")
        self.timeout = timeout
        self._client = SimpleUDPClient(host, send_port)
        self._responses: "queue.Queue[tuple[str, tuple]]" = queue.Queue()
        dispatcher = Dispatcher()
        dispatcher.set_default_handler(self._on_message)
        self._server = ThreadingOSCUDPServer(("0.0.0.0", receive_port), dispatcher)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def _on_message(self, address: str, *args: Any) -> None:
        self._responses.put((address, args))

    def send(self, address: str, *args: Any) -> None:
        """Fire-and-forget (set di parametri, transport, note)."""
        self._client.send_message(address, list(args))

    def query(self, address: str, *args: Any) -> Optional[tuple]:
        """Invia e attende la risposta sullo stesso address."""
        while not self._responses.empty():
            try:
                self._responses.get_nowait()
            except queue.Empty:
                break
        self._client.send_message(address, list(args))
        import time
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            try:
                addr, payload = self._responses.get(timeout=0.1)
            except queue.Empty:
                continue
            if addr == address:
                return payload
        return None

    def close(self) -> None:
        self._server.shutdown()
