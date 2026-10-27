"""Trasporto dei server MCP di LIVEMIND, uguale per tutti i client.

- stdio (default): Claude Desktop, Claude Code, OpenAI Codex CLI, Cursor...
- --http [porta]: streamable HTTP su 127.0.0.1:<porta>/mcp, per i client che
  accettano solo server remoti (ChatGPT developer mode). Va esposto con un
  tunnel HTTPS (vedi docs/SETUP.md): chi ha l'URL comanda Live, tenerlo privato.
"""
from __future__ import annotations

import sys

DEFAULT_HTTP_PORT = 8000


def parse(argv: list[str]) -> tuple[str, int | None]:
    """('stdio', None) oppure ('streamable-http', porta)."""
    if "--http" not in argv:
        return "stdio", None
    i = argv.index("--http")
    nxt = argv[i + 1] if i + 1 < len(argv) else ""
    return "streamable-http", int(nxt) if nxt.isdigit() else DEFAULT_HTTP_PORT


def run(server, argv: list[str] | None = None) -> None:
    transport, port = parse(sys.argv[1:] if argv is None else argv)
    if transport == "stdio":
        server.run()
        return
    server.settings.host = "127.0.0.1"  # mai 0.0.0.0: l'accesso esterno passa solo dal tunnel
    server.settings.port = port
    print(f"[livemind] MCP HTTP su http://127.0.0.1:{port}/mcp", file=sys.stderr)
    server.run(transport="streamable-http")
