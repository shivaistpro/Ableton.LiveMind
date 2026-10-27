# Setup di LIVEMIND sul tuo PC

Guida per un nuovo utente, da zero. Vale sia per Claude (Desktop / Code) sia
per OpenAI (Codex CLI / ChatGPT). Puoi anche dare questo file al tuo agente IA
e chiedergli di eseguire i passi con te.

Nei comandi, `<LIVEMIND_DIR>` e' la cartella dove cloni la repo.

## 1. Requisiti

- Windows 10/11 (cattura audio WASAPI, automazione UI e percorsi di default
  sono pensati per Windows; il canale LOM funziona anche su macOS)
- Ableton Live 12
- Python 3.10+ nel PATH, Git
- Un client IA con supporto MCP: Claude Desktop, Claude Code, OpenAI Codex
  CLI, oppure ChatGPT (piano Plus/Pro/Business/Enterprise/Edu, developer mode)

## 2. Clona e installa le dipendenze

```cmd
git clone https://github.com/shivaistpro/Ableton.LiveMind.git "<LIVEMIND_DIR>"
cd /d "<LIVEMIND_DIR>"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` include anche moduli opzionali (webcam, voce, Command
Center, mastering offline): se uno non si installa, il resto funziona lo stesso.

## 3. Adatta i percorsi al tuo PC

```cmd
copy .env.example .env
```

Apri `.env` e decommenta solo le righe che non vanno bene col default
(cartella output, cartelle dei set `.als`, User Library di Ableton se e' su
OneDrive, KICK 3, Ozone). Elenco completo nella sezione "Configurazione
percorsi" del `README.md`. `.env` resta sul tuo PC, non va mai in Git.

## 4. Installa i Remote Script in Ableton

**LiveMind** (canale LOM, consigliato):

```cmd
python -m livemind.install
```

Copia `remote_script/LiveMind` in `<User Library>\Remote Scripts\LiveMind`.

**AbletonOSC** (canale OSC, opzionale ma utile): scarica
<https://github.com/ideoforms/AbletonOSC/archive/refs/heads/master.zip>,
estrai in `<User Library>\Remote Scripts\AbletonOSC` (rinomina da
`AbletonOSC-master`).

Verifica: `python -m livemind.install --check`.

In Live: `Preferences > Link/Tempo/MIDI > Control Surface` -> **LiveMind** in
uno slot e **AbletonOSC** in un altro. Riavvia Live. Nel `Log.txt` di Live deve
comparire `LiveMind: in ascolto su 127.0.0.1:9005`.

## 5. Collega il tuo client IA

Tre server MCP, tutti da lanciare con la cartella della repo come working dir:

| Nome | Comando | Note |
|---|---|---|
| `livemind-lom` | `python -m livemind.mcp_server_lom` | LOM completa, consigliato |
| `livemind-ableton` | `python -m livemind.mcp_server` | richiede AbletonOSC |
| `livemind-exec` | `python -m livemind.local_exec_mcp` | shell senza conferme: opzionale, **solo locale** |

Usa il Python del venv (`<LIVEMIND_DIR>\.venv\Scripts\python.exe`) se
`python` nel PATH non e' quello con le dipendenze.

### Claude Code

Gia' configurato: `.mcp.json` nella radice. Lancia `claude` dentro
`<LIVEMIND_DIR>`, approva i server, verifica con `claude mcp list`.
Le istruzioni per l'agente arrivano da `CLAUDE.md` -> `AGENTS.md`.

### Claude Desktop

`%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "livemind-lom": {
      "command": "<LIVEMIND_DIR>\\.venv\\Scripts\\python.exe",
      "args": ["-m", "livemind.mcp_server_lom"],
      "cwd": "<LIVEMIND_DIR>"
    },
    "livemind-ableton": {
      "command": "<LIVEMIND_DIR>\\.venv\\Scripts\\python.exe",
      "args": ["-m", "livemind.mcp_server"],
      "cwd": "<LIVEMIND_DIR>"
    }
  }
}
```

Riavvia Claude Desktop. Per dargli le istruzioni operative, aggiungi
`AGENTS.md` alla conoscenza di un Project, o incollalo come istruzioni.

### OpenAI Codex CLI

Gia' configurato: `.codex/config.toml` (attivo se il progetto e' "trusted").
Lancia `codex` dentro `<LIVEMIND_DIR>`: legge `AGENTS.md` da solo.
Per averlo ovunque, copia i blocchi in `~/.codex/config.toml` aggiungendo
`cwd = "<LIVEMIND_DIR>"`.

### ChatGPT (web/desktop, developer mode)

ChatGPT accetta solo server MCP **remoti** (HTTP), quindi:

1. Avvia il server in HTTP sul tuo PC:
   ```cmd
   python -m livemind.mcp_server_lom --http 8000
   ```
   Ascolta solo su `http://127.0.0.1:8000/mcp`.
2. Esponilo con un tunnel HTTPS, per esempio
   `cloudflared tunnel --url http://127.0.0.1:8000` o `ngrok http 8000`.
3. In ChatGPT: `Settings > Apps > Advanced settings` -> attiva **Developer
   mode** -> **Create app**, URL = `https://<tunnel>/mcp`.
4. In chat: menu **+** -> Developer mode -> seleziona l'app. Incolla
   `AGENTS.md` nelle istruzioni (o in un Project/GPT) perche' sappia come lavorare.

**Sicurezza**: chiunque abbia l'URL del tunnel comanda il tuo Live. Non
condividerlo, chiudi il tunnel quando hai finito. `livemind-exec` rifiuta
`--http` di proposito: una shell senza conferme non va mai esposta in rete.

### Agenti in sandbox senza rete verso il PC

Usa il bridge a file: doppio click su `bridge.bat`, lascia la finestra
aperta; l'agente scrive in `bridge/inbox.jsonl` e legge
`bridge/reply.<id>.json` (protocollo in `AGENTS.md`).

## 6. Verifica

Con Live aperto:

```cmd
pytest -q                                              # test senza Live
python -m livemind.app --no-vision --no-voice --no-brain   # deve stampare: [live] connesso
```

Poi chiedi all'agente: *"chiama connection_status e dimmi quante tracce ha il
set"*. Primo controllo audio: *"cattura 10 secondi dell'uscita e mostrami lo
spettrogramma"* (`python -m livemind.audio.loopback 10 test`).

## 7. Reference per genere (opzionale)

Metti alcuni master del genere in `references/<genere>/` (`hardtek`,
`tekno_tribe`, `acid`, `hardflor`, o una cartella nuova). Sono tuoi e restano
fuori da Git. Uso: `python -m livemind.audio.reference mix.wav --genre hardtek`.

## 8. I tuoi script personali

Gli script legati a un tuo set (indici, nomi di tracce, coordinate dello
schermo) tienili in `tools/` ma escludili da Git aggiungendoli a
`.git/info/exclude`: restano solo sul tuo PC. Per script riusabili segui il
modello "Creare nuovi strumenti" in `AGENTS.md`: percorsi da `_paths`, tracce
e device cercati per nome.

## Problemi comuni

| Sintomo | Causa / soluzione |
|---|---|
| `connection_status` LOM fallisce | Remote Script non selezionato o Live da riavviare dopo `livemind.install` |
| Cattura audio `0x8889000a` | driver in modalita' esclusiva (ASIO4ALL): usa il driver WASAPI/MME |
| `list_projects` non trova i set | aggiungi le cartelle a `LIVEMIND_PROJECT_DIRS` in `.env` |
| Script Ozone: "imposta LIVEMIND_MASTER_SRC" | indica in `.env` il mix da masterizzare |
| Comando `claude` non trovato (Command Center) | installa Claude Code CLI e mettilo nel PATH |
