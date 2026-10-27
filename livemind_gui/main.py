"""LIVEMIND Command Center — client desktop (PySide6).

Parla con livemind.core_server via HTTP locale (127.0.0.1:8765); il core a
sua volta invoca Claude Code CLI in modalita' headless (abbonamento, non API
key a consumo) e mantiene lo stato su disco — chiudere/riaprire questa GUI
non fa perdere ne' la sessione ne' il log dei job.

Avvio: python -m livemind_gui.main
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTextEdit, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QLabel,
    QComboBox,
)

ROOT = Path(__file__).resolve().parent.parent
THEMES_DIR = Path(__file__).resolve().parent / "themes"
CORE_URL = "http://127.0.0.1:8877"
POLL_MS = 800

sys.path.insert(0, str(ROOT))
from livemind.lom_client import LomClient  # noqa: E402
from livemind_gui.tts import Speaker  # noqa: E402


def ensure_core_running(timeout_s: float = 10.0) -> bool:
    """Avvia livemind.core_server se non e' gia' su, senza legarlo al ciclo
    di vita di questa finestra (deve sopravvivere alla chiusura della GUI)."""
    try:
        requests.get(CORE_URL + "/health", timeout=0.5)
        return True
    except requests.RequestException:
        pass
    kwargs = {}
    if os.name == "nt":
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        kwargs["creationflags"] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "livemind.core_server:app",
         "--host", "127.0.0.1", "--port", "8877"],
        cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(0.3)
        try:
            requests.get(CORE_URL + "/health", timeout=0.5)
            return True
        except requests.RequestException:
            continue
    return False


class PollWorker(QThread):
    """Fa tutte le chiamate HTTP/TCP (core + LOM) fuori dal thread UI — se
    una risposta e' lenta, non blocca la finestra (drag, resize, input)."""
    data_ready = Signal(dict)

    def __init__(self, lom_client: LomClient, parent=None):
        super().__init__(parent)
        self._lom = lom_client
        self._jobs_seen = 0
        self._running = True

    def stop(self) -> None:
        self._running = False
        self.wait(2000)

    def run(self) -> None:
        while self._running:
            payload: dict = {"status": None, "new_jobs": [], "lom_ok": False}
            try:
                payload["status"] = requests.get(CORE_URL + "/status", timeout=1).json()
            except requests.RequestException:
                pass
            try:
                new = requests.get(CORE_URL + "/jobs",
                                    params={"since": self._jobs_seen}, timeout=1).json()
                if isinstance(new, list):
                    for job in new:
                        self._jobs_seen += 1
                        if isinstance(job, dict):
                            payload["new_jobs"].append(job)
            except requests.RequestException:
                pass
            try:
                payload["lom_ok"] = bool(self._lom.ping().get("ok"))
            except Exception:
                payload["lom_ok"] = False
            self.data_ready.emit(payload)
            self.msleep(POLL_MS)


class LiveMindWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LIVEMIND — Command Center")
        self.resize(1100, 700)

        self._last_reply_shown = ""
        self._lom = LomClient(timeout=1.5)
        self._speaker = Speaker()

        self._build_ui()
        self._apply_theme("dark_command")

        self._poller = PollWorker(self._lom)
        self._poller.data_ready.connect(self._on_poll_data)
        self._poller.start()

    # ---- UI ----

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(6)

        top = QHBoxLayout()
        title = QLabel("LIVEMIND")
        title.setStyleSheet("font-weight: bold; letter-spacing: 2px;")
        top.addWidget(title)
        top.addStretch(1)

        self.lbl_core = self._status_label("core: ...")
        self.lbl_lom = self._status_label("lom: ...")
        top.addWidget(self.lbl_core)
        top.addWidget(self.lbl_lom)

        self.btn_tts = QPushButton("TTS")
        self.btn_tts.setCheckable(True)
        self.btn_tts.setEnabled(self._speaker.available)
        self.btn_tts.toggled.connect(self._toggle_tts)
        top.addWidget(self.btn_tts)

        self.theme_box = QComboBox()
        for f in sorted(THEMES_DIR.glob("*.qss")):
            self.theme_box.addItem(f.stem)
        self.theme_box.currentTextChanged.connect(self._apply_theme)
        top.addWidget(self.theme_box)
        root_layout.addLayout(top)

        splitter = QSplitter(Qt.Horizontal)
        root_layout.addWidget(splitter, 1)

        chat_panel = QWidget()
        chat_layout = QVBoxLayout(chat_panel)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        chat_layout.addWidget(self.transcript, 1)
        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("scrivi a LIVEMIND...")
        self.input.returnPressed.connect(self._send)
        self.btn_send = QPushButton("Invia")
        self.btn_send.clicked.connect(self._send)
        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.btn_send)
        chat_layout.addLayout(input_row)
        splitter.addWidget(chat_panel)

        jobs_panel = QWidget()
        jobs_layout = QVBoxLayout(jobs_panel)
        jobs_layout.setContentsMargins(0, 0, 0, 0)
        jobs_layout.addWidget(QLabel("Job"))
        self.job_list = QListWidget()
        jobs_layout.addWidget(self.job_list, 1)
        splitter.addWidget(jobs_panel)
        splitter.setSizes([750, 350])

    def _status_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setProperty("role", "status")
        return lbl

    def _set_status(self, label: QLabel, text: str, ok: bool | None) -> None:
        label.setText(text)
        role = "status" if ok is None else ("status-ok" if ok else "status-off")
        label.setProperty("role", role)
        label.style().unpolish(label)
        label.style().polish(label)

    def _apply_theme(self, name: str) -> None:
        path = THEMES_DIR / f"{name}.qss"
        if path.exists():
            self.setStyleSheet(path.read_text(encoding="utf-8"))

    # ---- azioni ----

    def _toggle_tts(self, checked: bool) -> None:
        self._speaker.enabled = checked

    def _send(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self._append_chat("tu", text)
        try:
            r = requests.post(CORE_URL + "/chat", json={"message": text}, timeout=3)
            data = r.json()
            if not data.get("ok"):
                self._append_chat("sistema", data.get("error", "errore sconosciuto"))
        except requests.RequestException as e:
            self._append_chat("sistema", f"core non raggiungibile: {e}")

    def _append_chat(self, who: str, text: str) -> None:
        self.transcript.append(f"<b>{who}&gt;</b> {text}")

    # ---- polling (i dati arrivano gia' pronti dal thread worker) ----

    def _on_poll_data(self, payload: dict) -> None:
        status = payload.get("status")
        if status is None:
            self._set_status(self.lbl_core, "core: OFF", False)
        else:
            running = status.get("status") == "running"
            self._set_status(self.lbl_core, f"core: {'busy' if running else 'idle'}", not running or None)
            self.btn_send.setEnabled(not running)
            reply = status.get("last_reply") or ""
            if not running and reply and reply != self._last_reply_shown:
                self._append_chat("livemind", reply)
                self._speaker.speak(reply)
                self._last_reply_shown = reply

        added = False
        for job in payload.get("new_jobs", []):
            jtype = job.get("type", "?")
            name = job.get("name")
            job_status = job.get("status", "")
            label = name or jtype
            detail = job.get("detail")
            detail_str = json.dumps(detail, ensure_ascii=False) if isinstance(detail, (dict, list)) else str(detail or "")
            if len(detail_str) > 100:
                detail_str = detail_str[:100] + "…"
            line = f"[{job_status}] {label}: {detail_str}" if detail_str else f"[{job_status}] {label}"
            self.job_list.addItem(QListWidgetItem(line))
            added = True
            if jtype == "tool_use":
                self._append_chat("tool", f"{name} &rarr; {detail_str}")
        if added:
            self.job_list.scrollToBottom()

        lom_ok = payload.get("lom_ok")
        self._set_status(self.lbl_lom, f"lom: {'OK' if lom_ok else 'OFF'}", lom_ok)

    def closeEvent(self, event) -> None:
        self._poller.stop()
        self._speaker.stop()
        super().closeEvent(event)


def main() -> None:
    if not ensure_core_running():
        print("[core] non risponde su 127.0.0.1:8877 — avvialo a mano: "
              "python -m uvicorn livemind.core_server:app --port 8877")
    app = QApplication(sys.argv)
    win = LiveMindWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
