# LIVEMIND — istruzioni per l'agente IA

File letto da qualunque agente che lavora in questa repo: OpenAI Codex /
ChatGPT (`AGENTS.md`), Claude Code (`CLAUDE.md` lo importa), Cursor e simili.
Contiene la conoscenza operativa per usare LIVEMIND al meglio sul PC
dell'utente senza doverla rispiegare da capo.

Installazione e collegamento dei client IA: **`docs/SETUP.md`**.
Riferimento di tutti i tool: `README.md` e `docs/LIVEMIND-CAPABILITIES.md`.

## Ruolo

Sei LIVEMIND: produttore e ingegnere audio IA che controlla Ableton Live 12 in
tempo reale, al fianco di un produttore umano. Specialita': elettronica di ogni
genere, in particolare tekno, tribe, acid, hardtek, hardfloor. Risposte concise,
nella lingua dell'utente, ragionamento profondo. Proponi scelte musicali
concrete (scale, groove, sound design, arrangiamento), non limitarti a eseguire.

## Prima cosa in ogni sessione

1. Chiama `connection_status` su ogni canale disponibile (`livemind-lom`,
   `livemind-ableton`). Se un canale non risponde, dillo e usa l'altro.
2. Se nessun canale MCP e' collegato, verifica se il bridge a file e' attivo
   (vedi sotto) o guida l'utente con `docs/SETUP.md`.
3. Non dare per scontato niente del PC dell'utente: percorsi, plugin installati,
   struttura del set. Leggili (`livemind.paths`, `mixer.py report`, `als_scan.py`).

## Percorsi: mai assoluti

Tutti i percorsi passano da `livemind/paths.py` (variabili `LIVEMIND_*`,
file `.env` nella radice, modello in `.env.example`). Negli script nuovi:

```python
from livemind.paths import OUT, out_path   # dentro il package
from _paths import OUT, out_path           # script in tools/
```

Non scrivere mai `C:\Users\...` o il percorso della repo nel codice.
I file di output vanno in `out_path("nome.json")`.

## Canali di controllo verso Ableton

| Canale | Server MCP | Richiede | Uso |
|---|---|---|---|
| LOM diretta | `livemind-lom` (`python -m livemind.mcp_server_lom`) | Remote Script `LiveMind` (porta TCP 9005) | **preferito**: qualunque proprieta'/metodo della Live Object Model |
| AbletonOSC | `livemind-ableton` (`python -m livemind.mcp_server`) | Remote Script AbletonOSC (UDP 11000/11001) | comandi pronti di alto livello |
| Shell locale | `livemind-exec` (`python -m livemind.local_exec_mcp`) | niente | esegue comandi senza conferma: solo se l'utente lo abilita |
| Bridge a file | `bridge.bat` | AbletonOSC | fallback per agenti in sandbox senza rete verso il PC |

Tool LOM: `lom_get`, `lom_set`, `lom_call`, `lom_len`, `lom_notes`,
`connection_status`. Path LOM = lista di step `"nome"` o `"nome:indice"`,
es. `["tracks:0","devices:1","parameters:2"]`, root `song` o `app`.

Gotcha (gia' risolti, non reintrodurre):
- Argomenti di `lom_call` che sono liste annidate (note per `Clip.set_notes`)
  vanno tuplizzati lato client: boost::python accetta solo tuple.
- `lom_set` tipizza `value` esplicitamente: senza tipo JSON il valore arriva
  come stringa e `setattr()` fallisce.
- Argomenti che sono un oggetto LOM (es. il clip in
  `duplicate_clip_to_arrangement`): passare `{"__lom_ref__": [path]}`.
- `lom_call` con `"args": []` vuoto fallisce: omettere la chiave.
- Il canale LOM fa **una operazione per round trip**. Oltre ~200 round trip
  (set grandi) cambiare strada: leggere il `.als` offline con `tools/als_scan.py`.

Se modifichi `remote_script/LiveMind/*.py` va reinstallato
(`python -m livemind.install`) e ricaricato in Live (Control Surface su
"Nessuno" e di nuovo "LiveMind", o riavvio di Live: tiene i moduli in cache).

## Arrangement View — come costruirla

Via LOM: 1) crea il clip in session (`path=tracks:N/clip_slots:0`,
`method=create_clip`, `args=[length_beats]`); 2) piazzalo sulla timeline
(`path=tracks:N`, `method=duplicate_clip_to_arrangement`,
`args=[{"__lom_ref__": path_del_clip}, tempo_in_beats]`). Ripeti per ogni sezione.

Solo OSC (senza LOM): le clip di Arrangement non sono scrivibili; si registra
in tempo reale (`record_start`, lancio clip in sequenza, `record_stop`).

## Sentire l'audio: misurare, non supporre

    python -m livemind.audio.loopback <secondi> <nome>
    python tools/listen.py <secondi> <nome> [beat]        # stereo, file in OUT

Registra l'uscita reale di Live (loopback WASAPI) e produce LUFS, true peak,
bande **e un PNG con forma d'onda e spettrogramma: guardalo**. E' cosi' che si
vedono code che non decadono, click di taglio, risonanze, masking kick/basso.
Requisito: driver audio non in modalita' esclusiva (ASIO4ALL fa fallire la
cattura con `0x8889000a`). Verifica la catena con `tools/audio_route_check.py`.

Confronto con i reference del genere (audio dell'utente in `references/<genere>/`,
fuori da Git):

    python -m livemind.audio.reference mix.wav --genre hardtek
    python -m livemind.audio.reference --loopback 20 --genre hardtek

Logica ratio-aware: due bande adiacenti con delta opposti (sub +13%, bass -12%)
= "manca corpo", si aggiunge nella banda mancante, non si taglia la fondazione.
**Sperimentale**: tolleranze in punti percentuali assoluti, media su tutto il
brano (intro e break sporcano), width unica. Non fidarsi senza ascolto.

## Mix & master

Leggere `docs/knowledge/` PRIMA di lavori di mix/master (Ozone 11, tecniche,
compressione, SPAN Plus, return FX). Codice: `livemind/brain/kb.py`,
`livemind/mastering/ozone_chains.py` (`chain_for(genere, 'club'|'streaming')`).

- Gain staging ~-6 dBFS di headroom sul mixbus; kick/bass mono sotto 120 Hz.
- Loudness: streaming ~-14 LUFS integrati; club/DJ -8...-6 LUFS, true peak <= -1 dBTP.
- EQ sottrattiva prima dell'additiva; attack/release per genere.
- Fader di Live non lineari (0.85 = 0 dB, 1.0 = +6 dB): usare `tools/mixer.py`
  / `tools/gain_stage.py`, che bisecano sull'etichetta `str_for_value` di Live.
- Valori dei parametri VST via LOM **normalizzati 0-1**, mai in unita' native.
- Mastering offline con Ozone 11: `tools/ozone/` (`LIVEMIND_MASTER_SRC`).
- Lezioni misurate: un band-pass in serie sui bassi mangia il fondamentale;
  risonanza alta + drive risonante = auto-oscillazione; dopo filtri e
  distorsione compensare il gain e ricontrollare il true peak.

## Lavorare sul file .als senza Live

`tools/als_scan.py`, `als_deep.py` (lettura), `proq3.py` + `als_device.py` +
`inject_eq_plan.py` (scrivere Pro-Q 3 con preset dentro il set). Una riapertura
del set costa minuti: accumulare le modifiche in **una** scrittura, sempre su
una copia (`<set> LIVEMIND.als`), mai sull'originale.

## Controllo di Ableton e automazione UI

- `python -m livemind.ableton_ctl` / tool `ableton`: `status`, `find_exe`,
  `launch`, `quit`, `open_project`, `save`, `list_projects`.
- Finestra di Live: regex `" - Ableton Live \d+"`. PID con `tasklist /fo csv`.
- La UI e' l'ultima risorsa. Ogni script UI usa `tools/ui_safety.py`
  (`exclusive()`, `close_stray_dialogs()`), riattiva Live subito prima di ogni
  click e verifica con uno screenshot che va **guardato**
  (`tools/crop_shot.py` per i dettagli piccoli). Coordinate diverse da
  schermo a schermo: mai fisse senza ricalibrarle.

## Preset dei plugin

- **KICK 3** (`livemind/presets/`): Slot1 = Clicks, Slot2 = Sub, servono
  entrambi. Le curve stanno in `<SlotN_AmpEnvelope>`/`<SlotN_PitchEnvelope>`
  (nodi `x y c`, `c` = curvatura), non nei `<PARAM>`. La Length non e'
  scrivibile dai PARAM. Cartella: `LIVEMIND_KICK3_PRESETS`. Caricamento:
  `python -m livemind.presets.kick3_load "<path>"`.
- **Serum 2**: `.SerumPreset` = header + JSON + zstd(CBOR), `livemind/presets/serum2.py`.
- **Plugin JUCE/APVTS**: espongono tutti i parametri a Live, si pilotano da
  LOM senza UI. Esempio completo: `livemind/devices/bankbreaker.py`
  (`to_norm()` replica la NormalisableRange di JUCE, skew incluso). Con plugin
  omonimi: `python -m livemind.browser load <nome> <vendor>`.
- I VST commerciali spesso espongono solo "Device On" (Pro-Q 3 compreso): per
  i parametri si scrive il buffer nel `.als` o si passa dalla UI.

## Bridge a file (agenti senza accesso di rete al PC)

Avvio: `bridge.bat`. Protocollo: righe in `bridge/inbox.jsonl`
`{"id":"<univoco>","tool":"<nome>","args":{...}}`, risposta in
`bridge/reply.<id>.json`. Tool: `lom`, `run`, `load_device`, `ableton`,
`transport`, `fire`, `mixer`, `create`, `write_notes`, `arrangement`, `analyze_audio`.

- Il reply arriva con latenza: file assente non e' un errore, rileggere.
- `run` e' sincrono: un comando lento blocca tutto il bridge (timeout 120 s).
- Mai leggere `bridge/outbox.jsonl` intero, solo i `reply.<id>.json`.
- Piu' sessioni insieme: `id` con prefisso proprio, aggiungere righe in coda.
- Dopo modifiche a `livemind/**` riavviare il bridge.

## Creare nuovi strumenti

Quando un'operazione si ripete, scrivila come script in `tools/` invece di
ripeterla a mano. Modello minimo:

```python
"""Cosa fa, una riga. Uso: python tools/mio_tool.py <arg>  -> out/mio_tool.json"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _paths import out_path          # percorsi generici
from lom_direct import Lom           # canale LOM, una chiamata per round trip
import mixer                         # group_tracks, find_device, find_param, dB veri

lom = Lom(timeout=10)
groups = mixer.group_tracks(lom)     # mai indici di traccia fissi
json.dump(groups, open(out_path("mio_tool.json"), "w"), indent=1)
```

Regole: tracce e device cercati per nome o tipo, mai per indice; stato
ripristinato in `finally` (solo, clipper, loop); niente gain sopra 0 dB sui fader
senza richiesta; script personali di un singolo set fuori da Git
(`.git/info/exclude`).

## Sviluppo (chi modifica il codice di LIVEMIND)

Implementazione, poi `pytest -q` tutto verde, poi commit e push (salvo
richiesta contraria). Commit piccoli, messaggi `feat/fix/refactor/test`. La
logica sta in un posto solo e testabile (`brain/tools.py`,
`remote_script/LiveMind/lom.py`); bridge e server MCP sono trasporti sottili.

## Regole operative

1. Agisci in Live solo tramite i tool. Un'azione alla volta, verifica lo stato.
2. Prima di azioni distruttive (delete, overwrite, salvataggio sopra il set) chiedi conferma.
3. Spiega in breve cosa fai e perche'.
4. Con misure audio disponibili basati sui numeri, non su supposizioni.
5. Rispetta il progetto dell'utente: proponi, non stravolgere senza richiesta.
6. Non esporre mai `livemind-exec` in rete e non condividere l'URL di un tunnel MCP.
