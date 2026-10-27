"""Agente Claude: loop conversazione + tool-use verso Live."""
from __future__ import annotations
import os

from .knowledge import SYSTEM_PROMPT
from .tools import TOOLS, dispatch

try:
    import anthropic
    _HAS_ANTHROPIC = True
except ImportError:  # pragma: no cover
    _HAS_ANTHROPIC = False

MODEL = os.environ.get("LIVEMIND_MODEL", "claude-sonnet-4-5")
MAX_TOOL_ROUNDS = int(os.environ.get("LIVEMIND_MAX_ROUNDS", "40"))


class LiveMindAgent:
    def __init__(self, live, analyzer=None, loader=None, lom=None, api_key: str | None = None):
        if not _HAS_ANTHROPIC:
            raise RuntimeError("pip install anthropic")
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("Imposta ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=key)
        self.live = live
        self.analyzer = analyzer
        self.loader = loader
        self.lom = lom
        self.history: list[dict] = []

    def chat(self, user_message: str, on_action=None) -> str:
        """Un turno utente. Esegue tool call finché il modello non risponde con testo."""
        self.history.append({"role": "user", "content": user_message})
        for _ in range(MAX_TOOL_ROUNDS):
            resp = self.client.messages.create(
                model=MODEL, max_tokens=2048, system=SYSTEM_PROMPT,
                tools=TOOLS, messages=self.history)
            self.history.append({"role": "assistant", "content": resp.content})
            if resp.stop_reason != "tool_use":
                return "".join(b.text for b in resp.content if b.type == "text")
            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    if on_action:
                        on_action(block.name, block.input)
                    out = dispatch(block.name, block.input, self.live, self.analyzer, self.loader, self.lom)
                    results.append({"type": "tool_result",
                                    "tool_use_id": block.id, "content": out})
            self.history.append({"role": "user", "content": results})
        return ("(raggiunto il limite di azioni per turno: scrivi 'continua' "
                "e riprendo da dove ero rimasto)")
