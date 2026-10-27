# LIVEMIND — CLAUDE.md

Letto da Claude Code all'avvio in questa cartella (anche headless dal Command
Center via `claude -p`). Le istruzioni complete, uguali per ogni agente IA,
stanno in `AGENTS.md`:

@AGENTS.md

## Specifico di Claude

- **Claude Code**: i server MCP sono gia' dichiarati in `.mcp.json` (progetto).
  Al primo avvio approvali; `claude mcp list` per verificarli.
- **Claude Desktop**: registra i server in `claude_desktop_config.json` con
  `cwd` = cartella della repo (esempio in `docs/SETUP.md`), poi riavvia.
- **Sessioni in sandbox senza rete verso il PC**: il Remote Script non e'
  raggiungibile, usare il bridge a file (`bridge.bat`, vedi `AGENTS.md`).

## Command Center (client desktop, solo Claude)

`livemind/core_server.py` (FastAPI, porta **8877**) invoca la CLI `claude -p
... --resume` in headless: resta sull'abbonamento, non su una API key.
- Toglie `ANTHROPIC_API_KEY` dall'ambiente del sottoprocesso: altrimenti ha la
  precedenza sul login OAuth e da 401.
- Su Windows `claude` e' uno script `.cmd`: serve `shell=True`.
- In headless serve `--dangerously-skip-permissions` (nessuno risponde ai prompt).
- Stato e job log in `livemind/state/` (locale, fuori da Git).
- Client: `restart.bat` oppure `python -m livemind_gui.main` (PySide6).
