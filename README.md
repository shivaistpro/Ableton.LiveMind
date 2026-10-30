# LIVEMIND

Copilota AI per Ableton Live 12. Due strade per il controllo, complementari:

1. **[AbletonOSC](https://github.com/ideoforms/AbletonOSC)** — Remote Script di terze parti, gratuito e mantenuto dalla community. Copre transport, mixer, clip, device, scene, view: tutto ciò che serve nel 90% dei casi.
2. **Remote Script LiveMind** (`remote_script/LiveMind`) — Remote Script proprietario di questo progetto, accesso diretto alla Live Object Model (LOM) via socket TCP. Colma esattamente i buchi di AbletonOSC: rack chains, automation envelope sulle clip, browser reale, freeze/flatten — e in generale qualunque proprietà/metodo della LOM, tramite un path generico get/set/call, senza dover scrivere un wrapper per ognuno.

Include anche controllo webcam gestuale, analyzer audio LUFS/true-peak e server MCP standard: funziona con **Claude** (Desktop, Code) e con **OpenAI** (Codex CLI, ChatGPT developer mode), oppure con qualunque agente via bridge a file.

**Nuovo utente?** Parti da [`docs/SETUP.md`](docs/SETUP.md) (installazione e collegamento del client IA). Le istruzioni operative per l'agente stanno in [`AGENTS.md`](AGENTS.md) (letto da Codex/ChatGPT; `CLAUDE.md` lo importa per Claude).

## Indice

- [Architettura](#architettura)
- [Tre modalità di controllo](#tre-modalità-di-controllo)
- [Setup](#setup) (guida completa: [docs/SETUP.md](docs/SETUP.md))
- [Configurazione percorsi](#configurazione-percorsi)
- [Riferimento completo dei tool — canale AbletonOSC](#riferimento-completo-dei-tool--canale-abletonosc)
- [Riferimento completo dei tool — canale LiveMind (LOM diretta)](#riferimento-completo-dei-tool--canale-livemind-lom-diretta)
- [Quando usare quale canale](#quando-usare-quale-canale)
- [Vision (webcam)](#vision-webcam)
- [Test](#test)
- [Limiti noti](#limiti-noti)
- [Roadmap](#roadmap)

## Architettura

```
livemind/
  osc/
    client.py           AbletonOSCClient — UDP sincrono (invio 11000, risposta 11001)
    live.py              LiveController — wrapper Python su tutto l'address space AbletonOSC
    loader.py            DeviceLoader — carica VST dal browser via automazione UI
    paramfind.py         fuzzy match nomi parametro (per set_param_by_name)
  brain/
    tools.py             schema tool + dispatch() canale AbletonOSC — fonte di verità di bridge.py e mcp_server.py
    knowledge.py          system prompt per il brain Claude API (modalità legacy)
    agent.py              loop Claude API (modalità legacy)
  vision/                tracker MediaPipe, gesture, 3 modalità webcam (macro/gesture/airmidi)
  audio/                 analyzer.py — LUFS BS.1770, true peak, bilancio spettrale sul master
  voice/                 push-to-talk, VAD, trascrizione (faster-whisper)
  lom_client.py           LomClient — TCP sincrono verso il Remote Script LiveMind
  mcp_server_lom.py       server MCP stdio, canale LOM diretta (rack/automation/browser/freeze + accesso generico)
  bridge.py               BridgeServer — comandi via file JSONL condiviso (agenti in sandbox)
  mcp_server.py           server MCP (stdio o --http), canale AbletonOSC
  mcp_transport.py        stdio per Claude/Codex, streamable HTTP per ChatGPT
  paths.py                tutti i percorsi, configurabili da .env / variabili LIVEMIND_*
  install.py              installa il Remote Script nella User Library
  app.py                  entry point console (chat + webcam + bridge, tutto insieme)

remote_script/LiveMind/   Remote Script da installare in Ableton (vedi Setup)
  __init__.py              ControlSurface: avvia il server TCP, esegue i comandi sul main thread
  server.py                CommandServer — socket TCP thread-safe (accept + coda + drain)
  lom.py                   dispatch() generico sulla Live Object Model (get/set/call/len per path)
```

Due layer di verità distinti, uno per canale: `brain/tools.py` (dispatch AbletonOSC) e `remote_script/LiveMind/lom.py` (dispatch LOM diretta). Entrambi seguono lo stesso principio: la logica sta in un unico posto testabile, `bridge.py`/`mcp_server.py`/`mcp_server_lom.py` sono layer di trasporto sottili che la richiamano — zero duplicazione.

## Tre modalità di controllo

### 1. Bridge a file (agenti in sandbox senza rete verso il PC, canale AbletonOSC)

`python -m livemind.app` avvia anche un `BridgeServer` che fa polling ogni 250ms su `bridge/inbox.jsonl` e scrive le risposte in `bridge/outbox.jsonl`.

```jsonl
{"id":"abc-001","tool":"transport","args":{"action":"set_tempo","bpm":150}}
```

### 2. Server MCP — canale AbletonOSC (raccomandato per l'uso quotidiano)

```json
{
  "mcpServers": {
    "livemind-ableton": {
      "command": "python",
      "args": ["-m", "livemind.mcp_server"],
      "cwd": "<LIVEMIND_DIR>"
    }
  }
}
```

### 3. Server MCP — canale LiveMind / LOM diretta (rack, automation, browser, freeze, accesso generico)

Richiede il Remote Script `LiveMind` installato e selezionato in Ableton (vedi Setup punto 1b).

```json
{
  "mcpServers": {
    "livemind-lom": {
      "command": "python",
      "args": ["-m", "livemind.mcp_server_lom"],
      "cwd": "<LIVEMIND_DIR>"
    }
  }
}
```

Esempi pronti per Claude Desktop, Claude Code (`.mcp.json`), Codex CLI (`.codex/config.toml`) e ChatGPT (`--http` + tunnel) in [docs/SETUP.md](docs/SETUP.md). Riavvia il client dopo aver registrato uno o entrambi. Con Ableton aperto, i tool compaiono direttamente — nessun file, nessun `app.py` da tenere aperto. Primo comando di ogni sessione: `connection_status` (esiste su entrambi i canali).

## Setup

Prerequisiti: Ableton Live 12, Python 3.10+.

1a. **AbletonOSC** (canale base):
   [scarica lo zip](https://github.com/ideoforms/AbletonOSC/archive/refs/heads/master.zip), estrai in
   `Documents\Ableton\User Library\Remote Scripts\AbletonOSC` (rinomina la cartella da `AbletonOSC-master`).
   In Live: `Preferences > Link/Tempo/MIDI > Control Surface` → seleziona **AbletonOSC**.

1b. **Remote Script LiveMind** (canale LOM diretta — opzionale, serve solo per rack/automation/browser/freeze/accesso generico):
   `python -m livemind.install` (oppure copia a mano l'intera cartella `remote_script/LiveMind` dentro)
   `Documents\Ableton\User Library\Remote Scripts\LiveMind` (Windows: `%USERPROFILE%\Documents\Ableton\User Library\Remote Scripts\LiveMind`).
   Riavvia Live, poi `Preferences > Link/Tempo/MIDI > Control Surface` → seleziona **LiveMind** (in uno slot diverso da AbletonOSC: puoi tenerli entrambi attivi contemporaneamente).
   Verifica nel `Log.txt` di Live la riga `LiveMind: in ascolto su 127.0.0.1:9005`.

2. **Dipendenze Python**:
   ```cmd
   cd /d "<LIVEMIND_DIR>"
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Verifica connessione** (richiede Ableton aperto con AbletonOSC attivo):
   ```cmd
   python -m livemind.app --no-vision --no-voice --no-brain
   ```
   Deve stampare `[live] connesso: N tracce, TEMPO BPM`.

## Configurazione percorsi

Nessun path della macchina di sviluppo e' scritto nel codice. Copia `.env.example` in `.env` e adatta i valori: viene caricato in automatico. Nei comandi e nei
file di config `<LIVEMIND_DIR>` indica la cartella dove hai clonato la repo.
Tutti i percorsi passano da `livemind/paths.py` e si cambiano con variabili
d'ambiente (gli script in `tools/` li leggono tramite `tools/_paths.py`):

| Variabile | Default | Uso |
|---|---|---|
| `LIVEMIND_ROOT` | radice della repo (auto) | base di tutti i path relativi |
| `LIVEMIND_OUT` | `<LIVEMIND_DIR>\out` | render, catture loopback, screenshot, JSON di output |
| `LIVEMIND_PROJECT_DIRS` | `~\Documents\Ableton;~\Documents;~\Music` | dove `list_projects` cerca i `.als` (separatore `;` su Windows) |
| `LIVEMIND_KICK3_PRESETS` | `C:\ProgramData\Sonic Academy\Kick 3\User\Presets` | cartella User Presets di KICK 3 |
| `LIVEMIND_OZONE_VST3` | `C:\Program Files\Common Files\VST3\iZotope\Ozone 11.vst3` | plugin usato da `tools/ozone/*` |
| `LIVEMIND_USER_LIBRARY` | `~\Documents\Ableton\User Library` | dove `livemind.install` copia il Remote Script |
| `LIVEMIND_MASTER_SRC` | — (obbligatoria) | mix `.wav` da masterizzare offline con `tools/ozone/*` |
| `LIVEMIND_CLIPPER` | `StandardCLIP` | nome del clipper sul Main per `tools/master_*.py` |

Esempio (CMD):

```cmd
set LIVEMIND_MASTER_SRC=C:\percorso\del\mio_mix.wav
set LIVEMIND_PROJECT_DIRS=D:\Progetti Ableton;%USERPROFILE%\Music
python tools\ozone\ozrun.py config.json master.wav
```

Gli script che lavorano su un set aperto non usano indici di traccia fissi:
gruppi, Utility e clipper vengono trovati via LOM (`mixer.group_tracks`,
`mixer.find_device`, `mixer.find_param`).

## Riferimento completo dei tool — canale AbletonOSC

Ogni tool è disponibile identico sia via bridge JSONL (`{"tool": "...", "args": {...}}`) sia via MCP diretto. Definiti in `brain/tools.py`.

### Transport e sessione

| Tool | Parametri | Descrizione |
|---|---|---|
| `transport` | `action` (play\|stop\|record_on\|record_off\|metronome_on\|metronome_off\|set_tempo), `bpm` | Trasporto base |
| `fire` | `what` (scene\|clip\|stop_clip\|stop_all), `track`, `index` | Lancia/ferma scene e clip |
| `song_action` | `action` (undo\|redo\|capture_midi\|continue_playing\|trigger_session_record\|create_scene\|delete_scene\|duplicate_scene\|get_num_scenes), `index` | Azioni a livello song |
| `arrangement` | `action` (goto\|jump_by\|get_position\|loop_on\|loop_off\|set_loop_region\|punch\|add_cue_here\|next_cue\|prev_cue\|back_to_arrangement\|overdub_on\|overdub_off\|record_start\|record_stop), `beats`, `start`, `length`, `punch_in`, `punch_out` | Vista Arrangement, loop, cue point |

### Mixer e tracce

| Tool | Parametri | Descrizione |
|---|---|---|
| `mixer` | `track`, `param` (volume\|pan\|send\|mute\|solo\|arm), `value`, `send_index` | Controlli mixer per traccia |
| `track_meta` | `action` (get_name\|set_name\|get_color\|set_color), `track`, `name`, `color` | Nome e colore traccia |
| `create` | `what` (midi_track\|audio_track\|midi_clip), `track`, `clip`, `length_beats` | Crea tracce/clip |
| `delete_track` | `track` o `tracks` (lista) | Elimina tracce (distruttivo; alto→basso per indici stabili) |

### Clip e note MIDI

| Tool | Parametri | Descrizione |
|---|---|---|
| `write_notes` | `track`, `clip`, `notes` (lista `{pitch,start,duration,velocity}`) | Aggiunge note MIDI |
| `clip_property` | `action` (get\|set), `track`, `clip`, `prop`, `value` | Qualsiasi proprietà clip: name, color, color_index, loop_start/end, looping, gain, pitch_coarse/fine, warping, warp_mode, muted, start/end_marker, launch_mode, launch_quantization, legato... |
| `clip_notes_bulk` | `action` (get\|remove), `track`, `clip` | Legge o svuota tutte le note di una clip |
| `clip_slot` | `action` (has_clip\|create_clip\|delete_clip\|duplicate_clip_to\|fire\|stop), `track`, `clip`, `length_beats`, `dst_track`, `dst_clip` | Gestione slot: crea/cancella/duplica clip senza registrare a mano |

### Device e parametri (VST inclusi — KICK 3, Serum, ecc.)

| Tool | Parametri | Descrizione |
|---|---|---|
| `device_param` | `track`, `device`, `param` (indice), `value` (0-1 normalizzato) | Imposta un parametro per indice |
| `set_param_by_name` | `track`, `device`, `param_name` (fuzzy match), `value` | Imposta un parametro cercandolo per nome |
| `device_params_full` | `track`, `device` | **Nome + valore + valore leggibile (Hz/dB/ms) + min/max** per ogni parametro — usalo per verificare un preset dopo averlo scritto, non solo per leggerlo |
| `load_device` | `track`, `device_name` | Carica un device/VST dal browser (automazione UI: Live deve essere visibile, carica il primo risultato) |
| `get_state` | `what` (snapshot\|devices\|device_params), `track`, `device` | Stato progetto/traccia/device |

### Scene

| Tool | Parametri | Descrizione |
|---|---|---|
| `scene_property` | `action` (get\|set), `scene`, `prop`, `value` | name, color, color_index, tempo, tempo_enabled, time_signature_numerator/denominator, time_signature_enabled |

### Vista/selezione UI

| Tool | Parametri | Descrizione |
|---|---|---|
| `view` | `action` (get/set_selected_track\|scene\|device), `track`, `scene`, `device` | Legge/imposta cosa è selezionato nell'interfaccia di Live |

### Diagnostica

| Tool | Parametri | Descrizione |
|---|---|---|
| `app_info` | `what` (version\|test) | Versione Live installata, test di connettività base |
| `analyze_audio` | `seconds` | LUFS integrato/short-term, true peak dBTP, bilancio spettrale (richiede loopback audio) |
| `sample` | `path`, `track`, `clip` o `position`, `name` | Carica un file audio come clip audio (Live 12 `create_audio_clip`): session se `clip`, altrimenti arrangement a `position` beats |
| `dsp_render` | `src`, `dst`, `chain`, `oversample`, `tail_s`, `normalize_dbfs` | Catena di effetti Python (pedalboard) renderizzata offline: distortion, clipping, bitcrush, ladder, compressor, limiter, filtri/EQ, reverb, delay, chorus, phaser. Non lineari in oversampling |
| `connection_status` *(solo mcp_server)* | — | Verifica subito se AbletonOSC risponde — primo comando da chiamare ad ogni sessione |

### Layer generico OSC — copertura 100% dell'address space AbletonOSC

| Tool | Parametri | Descrizione |
|---|---|---|
| `osc_get` | `address`, `args` (lista) | GET grezzo su qualsiasi address OSC AbletonOSC documentato |
| `osc_set` | `address`, `args` (lista) | SET/CALL grezzo (fire-and-forget) su qualsiasi address |

Riferimento indirizzi: [deepwiki.com/ideoforms/AbletonOSC](https://deepwiki.com/ideoforms/AbletonOSC/4-api-reference).

## Riferimento completo dei tool — canale LiveMind (LOM diretta)

Definiti in `livemind/mcp_server_lom.py`, eseguiti da `remote_script/LiveMind/lom.py` dentro Ableton. A differenza del canale OSC, qui non c'è una lista fissa di comandi: 5 tool generici coprono l'**intera** Live Object Model.

| Tool | Parametri | Descrizione |
|---|---|---|
| `connection_status` | — | Verifica che il Remote Script LiveMind risponda — primo comando da chiamare |
| `lom_get` | `path`, `prop`, `root` (song\|app) | Legge una proprietà per path generico |
| `lom_set` | `path`, `prop`, `value`, `root` | Scrive una proprietà per path generico |
| `lom_call` | `path`, `method`, `args`, `root` | Chiama un metodo per path generico |
| `lom_len` | `path`, `root` | Lunghezza di una collezione (tracks, devices, chains, clip_slots...) |
| `lom_notes` | `action` (get_extended\|add\|set_extended\|remove), `path`, `notes` | Note MIDI via le API extended (Live 11+, formato dict) |

**path** è una lista di step `"nome"` o `"nome:indice"` a partire da `root` (`song` = Live Set, `app` = Application/browser). Esempi:

```
lom_get(path=["tracks:0"], prop="name")
  → nome della traccia 0

lom_len(path=["tracks:0","devices:0","chains"])
  → numero di chain nel rack in posizione 0 sulla traccia 0

lom_get(path=["tracks:0","devices:0","chains:0","devices:0","parameters:0"], prop="automation_state")
  → stato automazione (0=none) del primo parametro del primo device nella prima chain

lom_call(path=["tracks:0","devices:0","chains:0","devices:0","parameters:0"], method="re_enable_automation")
  → riattiva l'automazione disabilitata da un override manuale

lom_call(path=[], method="create_scene", args=[-1])
  → crea una scena in fondo

lom_call(path=["tracks:0"], method="freeze")
  → freeze traccia (DA VERIFICARE dal vivo: non è certo che 'freeze' sia esposto
    come metodo chiamabile della LOM in tutte le build di Live — se lom_call
    ritorna "non ha metodo 'freeze'", è un limite reale di Live, non un bug qui)

lom_notes(action="get_extended", path=["tracks:1","clip_slots:0","clip"])
  → tutte le note MIDI della clip, formato dict con pitch/start_time/duration/velocity
```

Perché generico invece di 200+ wrapper dedicati: ogni proprietà/metodo che Ableton aggiunge in futuro (o che semplicemente non abbiamo ancora wrappato) è già raggiungibile, senza bisogno di scrivere/testare codice nuovo nel Remote Script. Il prezzo è che il chiamante deve conoscere i nomi LOM (Track, Device, Chain, DeviceParameter, ClipSlot, Clip, Scene, Browser...) — non gravissimo per un brain AI con accesso a documentazione.

## Quando usare quale canale

| Serve... | Canale |
|---|---|
| Transport, mixer, clip base, device/parametri, scene, view | `livemind-ableton` (OSC) — più comandi di alto livello già pronti |
| Rack chains, macro nei rack | `livemind-lom` — `path` con step `"chains:N"` |
| Automation envelope su un parametro (stato, riattivazione) | `livemind-lom` — `automation_state` / `re_enable_automation` |
| Browser reale (cercare/caricare device per query, non solo primo risultato UI) | `livemind-lom` — `path=["browser", ...]`, `root="app"` |
| Freeze/flatten traccia | `livemind-lom` — **da verificare dal vivo**, vedi sopra |
| Qualunque proprietà/metodo LOM senza un wrapper dedicato | `livemind-lom` — `lom_get`/`lom_set`/`lom_call` generico |

## Vision (webcam)

Tre modalità, attivabili da console (`/mode macro|gesture|airmidi|off`):

- **MACRO** — posizione mani (X/Y) → 4 parametri/macro continui
- **GESTURE** — palmo=stop all, pugno=rec, indice=scena 1, due dita=scena 2, pollice su=tap tempo
- **AIRMIDI** — griglia 4×2 in aria, gesto "point" → note MIDI da C1 (per un Drum Rack)

## Test

```cmd
cd /d "<LIVEMIND_DIR>"
pytest -q
```

Canale AbletonOSC: `brain/tools.py` e `mcp_server.py` testati con un `FakeLive` (nessuna dipendenza da Ableton/rete). Canale LiveMind: `remote_script/LiveMind/lom.py` testato con oggetti Python fittizi al posto di Track/Device/Clip reali (`tests/test_lom.py`), `remote_script/LiveMind/server.py` testato con un vero socket TCP locale simulando il main-thread tick di Live (`tests/test_command_server.py`), `livemind/mcp_server_lom.py` testato con un `FakeLomClient` (`tests/test_mcp_server_lom.py`). Nessuno di questi test richiede un'istanza reale di Ableton Live — il Remote Script vero e proprio (`__init__.py`, l'unico file che importa `_Framework`/`Live`) va verificato a mano nel proprio Ableton, non è testabile in CI.

## Limiti noti

- **Listener OSC non esposti** (`start_listen`/`stop_listen`, canale AbletonOSC): richiedono un canale asincrono persistente, incompatibile con request/response MCP.
- **`load_device` (canale OSC) automatizza la UI**: Live deve essere visibile, carica il primo risultato. Il canale LiveMind con `path=["browser",...]` può fare una ricerca più precisa, ma anche lì l'API Browser della LOM non è ufficialmente documentata da Ableton — va verificata dal vivo.
- **Freeze/flatten**: non è certo che siano esposti come metodi chiamabili della Live Object Model in ogni versione di Live (discussione aperta anche sul forum ufficiale Ableton). Il canale LiveMind ci prova via `lom_call`, ma se Live risponde "non ha metodo 'freeze'" è un limite reale della LOM, non un bug del Remote Script — l'alternativa resta l'automazione UI (tasto destro > Freeze Track).
- **Clip in Arrangement non scrivibili via OSC**: comporre in Session View, poi `arrangement.record_start` + fire delle clip per registrarle sulla timeline. Il canale LiveMind potrebbe coprire questo caso via `lom_call` su `Song.create_audio_track`/proprietà arrangement, non ancora testato dal vivo.
- **VST2**: parametri esposti solo dopo "Configure" in Live; VST3 sono automatici.
- **Remote Script non testabile qui**: `remote_script/LiveMind/__init__.py` importa `_Framework.ControlSurface`, disponibile solo dentro l'interprete Python embedded di Ableton Live (Windows/macOS, licenza proprietaria) — non esiste build Linux, quindi non è eseguibile in un sandbox headless. La logica (`lom.py`, `server.py`) è invece testata al 100% con mock/socket reali fuori da Ableton (vedi sezione Test); il collaudo end-to-end del Remote Script vero va fatto sul PC con Ableton aperto. Una volta registrato `livemind-lom` in Claude Desktop, i suoi tool compaiono direttamente nella sessione — il test dal vivo può avvenire chiamandoli in conversazione, senza bisogno di copiare/incollare risultati a mano.
- **Mount di rete**: se lavori su una cartella montata (SMB/rete), `git` va inizializzato con `git config --global --add safe.directory` e i tool di editing file possono troncare silenziosamente — verifica sempre con `wc -l` dopo una scrittura importante.

## Roadmap

- Verificare dal vivo freeze/flatten e Browser reale sul canale LiveMind, aggiornare questa doc con i nomi LOM confermati.
- Convenience tool ad alto livello sul canale LiveMind per le operazioni rack/automation più comuni (oggi coperte solo dal path generico).
- Groove/pattern helpers lato client (quantize/humanize note, generatori di bassline/drum pattern) — logica Python pura sopra `clip_notes_bulk`/`lom_notes`.
- Loopback audio configurato stabilmente per `analyze_audio` in produzione.

## Licenza

Uso consentito, modifiche e ridistribuzione no: vedi [`LICENSE`](LICENSE).
La repo non accetta contributi esterni (issue e pull request disattivate).
