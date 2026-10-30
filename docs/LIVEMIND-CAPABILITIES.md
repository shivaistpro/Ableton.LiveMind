# LIVEMIND — cosa so fare in Ableton (scheda rapida dei tool)

Scheda per qualunque agente IA (Claude, ChatGPT/Codex, altri) che debba
toccare Ableton Live, generare preset o misurare audio. Tutto il codice sta in
`<LIVEMIND_DIR>`. Istruzioni complete in `AGENTS.md`, installazione in `docs/SETUP.md`.

---

## 1. Come comando Ableton (bridge su file)

Se l'agente gira in una sandbox senza rete verso il PC, il Remote Script non e'
raggiungibile e i server MCP locali non servono: si passa dal bridge.

**Avvio**: doppio click su `<LIVEMIND_DIR>\bridge.bat`, lasciare la
finestra aperta.

**Protocollo**: scrivo righe in `bridge\inbox.jsonl`

    {"id":"<univoco>","tool":"<nome>","args":{...}}

e leggo `bridge\reply.<id>.json`.

**Tool disponibili**: `lom` (get/set/call/len/link su tutta la Live Object
Model — il canale piu' potente), `run` (shell Windows), `load_device`,
`ableton` (status/launch/quit/open_project/save/list_projects), `transport`,
`fire`, `mixer`, `create`, `write_notes`, `arrangement`, `analyze_audio`,
`sample` (carica un wav come clip audio, session o arrangement), `dsp_render`
(catena di effetti Python offline su un file: distorsione, comp, EQ, reverb...).

**Regole che evitano ore perse**
- Il reply arriva **con latenza**: file assente non significa errore, rileggere
  dopo qualche secondo.
- `run` e' **sincrono**: un comando lento blocca l'intero bridge. Mai lanciare
  scansioni che camminano tutto l'albero del browser (migliaia di round trip).
- Path LOM = **lista** di step: `["tracks:0","devices:1","parameters:2"]`.
- Per assegnare un OGGETTO LOM usare `action:"link"` con `value_path`.
- `lom_call` con `"args": []` vuoto fallisce: omettere la chiave.
- **Velocita'**: ogni comando LOM costa un tick di Live (fino a ~1 s con Live in
  secondo piano). Per molti comandi usare `LomClient.batch([...])`
  (`{"cmd":"batch","cmds":[...]}`): N comandi in un solo tick.
- Live 12.3+: `Track.insert_device("<nome device nativo>")` carica device Live
  senza browser/UI (Drift, Wavetable, Operator, EQ Eight, Compressor...). Non
  carica Max for Live (DS Kick...) ne' campioni in Simpler.
- Sidechain: `Compressor.available_input_routing_types` + `link` su
  `input_routing_type`, poi parametro `S/C On`.
- Mai leggere `bridge\outbox.jsonl` intero (decine di migliaia di token):
  solo i singoli `reply.<id>.json`.
- Modifiche a `livemind\**` richiedono riavvio del bridge, oppure invocare il
  modulo con `run: python -m livemind....`
- **Se un'altra sessione sta usando il bridge**, gli `id` devono essere
  distinti (prefisso proprio) e conviene non riscrivere l'inbox altrui:
  aggiungere righe in coda.

---

## 2. Come SENTO l'audio (unico modo di verificare davvero)

    python -m livemind.audio.loopback <secondi> <nome>

Registra l'uscita reale di Live (loopback WASAPI) e produce:
- misure: LUFS integrato, true peak dBTP, bilanciamento spettrale per bande
- **un PNG con forma d'onda e spettrogramma** in `bridge\audio\`

Il PNG va **guardato**: e' cosi' che si diagnosticano coda che non decade,
click di taglio, tempo sbagliato, risonanze che non si spengono, maschera tra
kick e basso.

Requisito: Live non deve tenere la scheda in esclusiva (con ASIO4ALL attivo la
cattura fallisce con `0x8889000a`).

### Confronto con i reference

    python -m livemind.audio.reference mix.wav --genre hardtek
    python -m livemind.audio.reference --loopback 20 --genre hardtek

Delta mix vs media dei reference in `references\<genere>\` (LUFS, LRA,
true peak, crest, stereo width, 7 bande in % di energia) + raccomandazioni
ratio-aware: sub alto e bass basso insieme = aggiungi corpo nel bass, non
tagliare il sub. Report JSON in `bridge\audio\`.

---

## 3. Controllo del processo Ableton e dei progetti

`python -m livemind.ableton_ctl` / tool `ableton`:
`status`, `find_exe`, `launch`, `quit`, `open_project`, `save`, `list_projects`.

- Finestra di Live: regex `" - Ableton Live \d+"` (cercare solo "Ableton Live"
  pesca anche le finestre del browser web).
- PID con `tasklist /fo csv` (il nome immagine contiene spazi).
- I set `.als` possono stare fuori da `Documents\Ableton`: aggiungere le cartelle
  in `LIVEMIND_PROJECT_DIRS` (separate da `;`) per `list_projects`.

---

## 4. Automazione della UI dei plugin (quando la LOM non arriva)

- La finestra di un VST si apre con **l'icona chiave inglese** nella barra del
  device (terza da sinistra). La mano e' l'indicatore MIDI remote, il
  rettangolo nero e' il pad X-Y.
- **Riattivare Live nello stesso script subito prima di ogni click**: il fuoco
  viene rubato e il click finisce su un'altra applicazione.
- Verificare sempre con uno screenshot e guardarlo. Per icone piccole,
  ritagliare e ingrandire con PIL.

---

## 5. Generazione preset

### KICK 3 — `livemind/presets/`
- Slot **1..5**. **Slot1 = Clicks** (campione nel blob `<DATA>`),
  **Slot2 = Sub** sintetizzato. Servono entrambi.
- Le curve **non** stanno nei `<PARAM ...AmpNodeN_x>` (restano a 1.0 anche nei
  preset buoni): stanno in `<SlotN_AmpEnvelope>` / `<SlotN_PitchEnvelope>`,
  nodi `x y c` dove `c` e' la curvatura.
- Pitch con `isKeytracked="1"`: y=1.0 = pitch base. Con `0`: `freq = 20*1000**y`.
- **La Length non e' scrivibile dai PARAM** (sta nel blob `<DATA>`): esprimere
  i nodi in ms e convertirli sulla finestra reale. Limite noto: la finestra del
  Sub e' ~170 ms.
- Cartella letta dal plugin (override `LIVEMIND_KICK3_PRESETS`):
  `C:\ProgramData\Sonic Academy\Kick 3\User\Presets\`
- Base buona: **`TRIBE_machines/02 TRIBE 909.preset`**.
  `TRIBE_analog` ha Slot1 spento e **non suona**.
- Caricamento automatico: menu ☰ -> "Load Preset" (dialogo file, si digita il
  percorso) — `python -m livemind.presets.kick3_load "<path>"`.

### Serum 2
`.SerumPreset` = header + JSON + zstd(CBOR). Decodificato e scrivibile
(`livemind/presets/serum2.py`).

---

## 6. VST JUCE/APVTS controllabili al 100% via LOM

I plugin JUCE/APVTS espongono **tutti** i parametri a Live, quindi si pilotano
interamente dal canale `lom`, senza UI. (I VST commerciali come KICK 3 spesso
espongono solo "Device On".)

**BankBreaker** (esempio di riferimento) — `livemind/devices/bankbreaker.py`, 38 parametri
mappati dal sorgente. Dual filter + 10 tipi di drive + loop risonante
(Reso Drive/Bloom) + envelope follower + LFO sincronizzabile.
- Con **plugin omonimi** nel browser scegliere per vendor:
  `python -m livemind.browser load BankBreaker <vendor>`.
- **I valori via LOM vanno normalizzati 0-1**, non in unita' native: scrivere
  220 su un cutoff in Hz viene rifiutato, 0.9 su un range 0-2 diventa 1.8.
  `to_norm()` replica la NormalisableRange di JUCE, skew incluso.
- Applicare con `bankbreaker.apply(track, device, dict)`.

Qualunque altro plugin JUCE/APVTS: stessa logica, stessa strada per il controllo.

---

## 7. Lezioni di mix trasferibili (misurate, non a orecchio)

- Un **band-pass in serie** sui bassi si mangia il fondamentale: su un kick il
  sub e' sceso di 10 dB. Usare LP risonante in parallelo.
- **Risonanza alta + drive risonante = auto-oscillazione**: bande fisse che
  suonano anche tra un colpo e l'altro (drone). Restare sotto soglia.
- Dopo filtri e distorsione si perdono ~10 dB: compensare col gain di uscita e
  **ricontrollare il true peak** (target <= -1 dBTP).
- Un envelope che si chiude di scatto produce un **click di taglio** udibile:
  serve un ultimo tratto verso lo zero.
- Con distorsione tenere l'**oversampling >= 2x** contro l'aliasing.

---

## 8. Leggere e MODIFICARE un set (`tools\`)

Il canale LOM fa **una operazione per round trip**: su un set grande (300+ tracce)
una scansione traccia-per-traccia supera i 15 minuti e blocca il bridge. Oltre
~200 round trip, cambiare strada. Questi strumenti lavorano sul file.

- **`als_scan.py <set.als> [beat_lo] [beat_hi] [out.json]`** — legge il `.als`
  (XML gzippato) e dumpa tracce, clip in arrangement nel range, catene device
  con i parametri, volumi, pan, routing, locatori. Due secondi invece di ore.
  In Live 12 il master e' `LiveSet/MainTrack` (non piu' `MasterTrack`), e i clip
  di arrangement stanno sotto `MainSequencer/ClipTimeable/ArrangerAutomation/Events`
  — cercarli in tutta la traccia pesca anche i clip di Session.
- **`proq3.py`** — scrive preset **FabFilter Pro-Q 3** `.ffp` da descrizioni di
  bande (`band(freq, shape, gain, q, slope, stereo, dyn_range)`). Self-check:
  `python proq3.py`.
- **`als_device.py`** — inserisce Pro-Q 3 **con il preset gia' dentro**
  direttamente nel `.als`. Live salva lo stato VST3 come Buffer esadecimale:
  `FFBS | ver 1 | 358 float | FQ3p | ver 3 | nome | ... | CuSV`, e i primi
  **334 float sono byte per byte identici al payload di un `.ffp`** (verificato
  rigenerando il buffer di un'istanza reale: identico). Serve un Pro-Q 3 gia'
  caricato a mano una volta, come modello XML. `track_index = -1` = master.
- **`inject_eq_plan.py <set.als> <piano.json> [out.als]`** — applica un piano di
  mix (preset Pro-Q 3 per traccia + gain in dB, tracce indicate per **nome**,
  indice o `MASTER`) in una sola passata sul `.als`. Di default scrive un nuovo
  file `<set> LIVEMIND.als`; rifiuta gain sopra 0 dB.
- **`mixer.py report [--chains] [--filter x]` / `mixer.py set gains.json`** — dal
  vivo via LOM: volumi in dB, solo/mute (avvisa se una traccia in solo zittisce
  tutto), catene di device; imposta i fader in dB per nome traccia. Il fader di
  Live non e' lineare in ampiezza (0.85 = 0 dB, 1.0 = +6 dB): il valore si trova
  bisecando sull'etichetta di Live stessa (`str_for_value`), non con una formula.
- **`stem_report.py <lista.json> <out.json>`** — misura file audio: LUFS, peak,
  crest, correlazione stereo, 7 bande, centroide, fondamentale. Legge anche i
  WAV float32 di Live (`wave` fallisce con "unknown format: 3"). La FFT e'
  **Welch su tutto il file**: una singola FFT sulla testa vede solo l'intro e
  fa sembrare il mix senza bassi.
- **`listen.py <sec> <nome>`** — cattura l'uscita di Live in **stereo**
  (`livemind.audio.loopback` collassa in mono e perde la correlazione).
- **`stem_listen.py [sec] [beat]`** — mette in solo ogni traccia gruppo del set
  (rilevate via LOM) e cattura, per capire chi porta davvero il basso. Il solo
  viene sempre tolto alla fine.
- **`render_block.py`** — render del blocco tra due locatori in WAV, pilotando il
  dialogo Esporta in modo protetto (`ui_safety`). **Per il range esatto**:
  loop via LOM, `Ctrl+Shift+L`, poi `Ctrl+Shift+R` (il dialogo si precompila).
- **`gain_stage.py idx=dB ...`**, **`eq_set.py`** / **`eq_apply.py`** — fader in dB veri
  e bande di EQ Eight via LOM, con ascolto opzionale `--listen`.
- **`ms_bands.py`**, **`measure_big.py`**, **`spectro.py`** — misure Mid/Side per banda,
  WAV enormi via memmap, forma d'onda + spettrogramma da guardare.
- **`crop_shot.py <src> <dst> x0 y0 x1 y1 [scale]`** — ritaglia e ingrandisce
  uno screenshot per leggere i dettagli piccoli della UI.

**Costo di una riapertura**: 3-4 minuti, e il Remote Script resta irraggiungibile
finche' i sample non sono caricati (aspettare che il `ping` LOM risponda).
Accumulare tutte le modifiche in **una** scrittura del `.als`.

Cosa NON e' controllabile via LOM: i VST commerciali espongono solo "Device On"
(Pro-Q 3 compreso). Per cambiarne i parametri, o si scrive il buffer nel `.als`,
o si passa dalla UI.
