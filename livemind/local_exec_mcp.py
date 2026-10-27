"""Server MCP minimale: esegue comandi shell locali senza dialoghi di permesso
per-chiamata (a differenza di computer-use, che richiede consenso schermo ad
ogni sessione). Una volta registrato in claude_desktop_config.json, ogni
chiamata a run() e' diretta — nessun popup.

ATTENZIONE: esecuzione comandi arbitrari sulla tua macchina, su tua richiesta
esplicita. Comandi distruttivi (cancellazioni, force push, ecc.) restano a
tuo rischio come da terminale normale.

Uso: registra in claude_desktop_config.json
  "livemind-exec": {
    "command": "python",
    "args": ["-m", "livemind.local_exec_mcp"],
    "cwd": "<LIVEMIND_DIR>"
  }
poi riavvia Claude Desktop.
"""
from __future__ import annotations
import subprocess
from typing import Optional


def build_tools() -> dict:
    def run(cmd: str, cwd: Optional[str] = None, timeout: int = 120) -> str:
        """Esegue un comando nella shell di Windows (cmd.exe) e ritorna
        exit code + stdout + stderr. cwd default: la cartella del progetto."""
        try:
            r = subprocess.run(cmd, shell=True, cwd=cwd, timeout=timeout,
                                capture_output=True, text=True)
        except subprocess.TimeoutExpired:
            return f"TIMEOUT dopo {timeout}s"
        except Exception as e:
            return f"ERRORE: {e}"
        out = f"[exit {r.returncode}]\n"
        if r.stdout:
            out += f"--- stdout ---\n{r.stdout}\n"
        if r.stderr:
            out += f"--- stderr ---\n{r.stderr}\n"
        return out

    return {"run": run}


def create_server():
    from mcp.server.fastmcp import FastMCP
    server = FastMCP(
        "livemind-exec",
        instructions=(
            "Esecuzione diretta di comandi shell su richiesta dell'utente, "
            "senza dialoghi di conferma per-chiamata. Passa cwd per "
            "posizionarti in una cartella diversa (default: quella di avvio "
            "del server, di norma la radice della repo)."
        ),
    )
    for name, func in build_tools().items():
        server.tool(name=name)(func)
    return server


def main() -> None:
    import sys
    if "--http" in sys.argv:  # shell remota senza conferme: solo stdio locale, mai esposta in rete
        raise SystemExit("livemind-exec gira solo su stdio: non esporlo via HTTP/tunnel.")
    create_server().run()


if __name__ == "__main__":
    main()
