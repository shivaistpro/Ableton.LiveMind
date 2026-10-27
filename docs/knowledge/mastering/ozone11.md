# iZotope Ozone 11 — riferimento completo per LIVEMIND

Fonte primaria: manuale ufficiale Ozone 11 (docs.izotope.com/ozone11, letto per intero).
Integrazioni: pagina "Why upgrade to Ozone 11" di iZotope, recensione Sound On Sound.
Tutto cio' che e' scritto come **fatto** viene dal manuale; cio' che e' marcato
**[uso]** e' prassi di mastering (nostra), da verificare a orecchio + misure.

---

## 0. Concetti base

- **Mothership** = plug-in `Ozone 11` completo: signal chain libera, Master Assistant,
  Stem Focus, Referencing, Codec Preview, Dither. Parte con catena **vuota**.
- **Component plug-in** = un modulo singolo come plug-in a se' (`Ozone 11 Maximizer`,
  `Ozone 11 Imager`, ...). Utili in Ableton per automatizzare/controllare un modulo
  alla volta, anche fuori dal master (es. Imager su un bus, Stabilizer su un synth).
- Dither: solo mothership + Maximizer component. Sum to Mono/Swap: mothership + Imager.
- **Delta** (ogni modulo): ascolti SOLO cio' che il modulo toglie/aggiunge. E' lo
  strumento n.1 per non esagerare: se nel delta senti kick/musica "vera", stai
  facendo troppo.
- **Gain Match** (I/O panel): A/B a pari volume. Regola d'oro: mai giudicare un
  master senza gain match (il piu' forte vince sempre all'orecchio).
- **Undo History con snapshot A/B/C/D**: salva 4 stati della catena e confrontali.
- I/O meter: Peak, RMS, RMS+Peak, K-System, **Momentary (400 ms), Short Term (3 s),
  Integrated**. Opzione "Detect true peaks" nelle I/O Options (di default i meter
  mostrano solo clip digitali, non inter-sample).
- Options → Spectrum: Tilt Slope default **3 dB/oct** (rumore rosa appare piatto).
  Average Time 10 s per leggere il bilanciamento tonale.

### Edizioni (verificare quale e' installata)
| | Elements | Standard | Advanced |
|---|---|---|---|
| Master Assistant | si | si | si |
| EQ, Dynamics, Imager, Exciter, Maximizer, Match EQ, moduli Vintage | no | si | si |
| Clarity, Stabilizer, Impact, Low End Focus, Master Rebalance, Spectral Shaper | no | no | si |
| Stem Focus, Transient/Sustain, Upward Compress, Vocal Balance | no | no | si |
| Component plug-in | no | no | si |

(Le fonti terze non concordano su alcuni dettagli; la tabella segue iZotope.
Prima di usare un modulo: aprire Ozone e controllare che compaia nel menu "+".)

### Channel Processing Modes (per modulo)
- **Stereo** (default), **Mid/Side**, **Left/Right**, **Transient/Sustain** (T/S:
  separa transiente e coda; se non processi, la somma ricostruisce il segnale identico).

| Modulo | M/S | L/R | T/S |
|---|---|---|---|
| Clarity | x | | x |
| Dynamics | x | | |
| Dynamic EQ | x | x | x |
| Equalizer | x | x | x |
| Exciter | x | | x |
| Imager | | | x |
| Impact | x | | |
| Match EQ | x | x | x |
| Low End Focus | x | | x |
| Spectral Shaper | x | | x |
| Stabilizer | x | | x |
| Vintage Compressor | x | | |
| Vintage EQ | x | x | x |

Performance: Stereo costa meno di M/S, L/R, T/S. Togliere i moduli non usati.

### Stem Focus (header, solo mothership)
`Full Mix | Vocals | Bass | Drums`: TUTTA la catena processa solo lo stem scelto
(separazione AI in tempo reale). **[uso]** Nella tekno: `Drums` per dare punch solo
alla ritmica (Impact/Dynamics), `Bass` per stringere il basso senza toccare il kick
(attenzione: il separatore puo' confondere kick distorto e basso — verificare col Delta).
Per processare uno stem e il resto diversamente servono DUE istanze di Ozone o
Master Rebalance.

---

## 1. Master Assistant (AI)

Flusso: Ozone sul Main track → tab Master Assistant → play della parte **piu' forte**
per almeno **8 s** (loop se piu' corta) → costruisce la catena.

- **Target**: 10 target di genere (da hit in classifica) + Cinematic, oppure
  **target da file reference** (analizza gli 8 s piu' forti del reference).
  Sub-target: Tonal Balance, Vocal Balance, Stereo Width (rapporto mid/side per banda),
  Dynamics (microdinamica = loudness brevissima / short-term), Loudness (LUFS integ.).
- Controlli macro:
  - **Equalizer** 0-200% → Amount di Equalizer 1.
  - **Maximizer** ±4 dB sulla Gain del Maximizer.
  - Destinazione: **Full Scale** = Output −0.1 dB, True Peak OFF;
    **Streaming** = Output −1 dB, True Peak ON.
  - **Vocal Balance** → Master Rebalance su Vocals (non con target custom).
  - **Dynamics Match** → Amount di Impact (4 bande).
  - **Width Match** → Amount dell'Imager (4 bande; puo' attivare Recover Sides,
    mai Stereoize; non allarga i bassi se gia' stretti).
  - **Clarity Amount** (tilt scelto dal genere), **Stabilizer Amount**.
- Tornare alla Module View e poi cambiare target **sovrascrive** le modifiche manuali.

**[uso] per LIVEMIND**: i target di fabbrica sono pop/hit di classifica, non tekno.
Usare SEMPRE un target da reference del genere giusto (i file in
`references/<genere>/`) e poi rifinire a mano. Master Assistant = punto di partenza,
non verdetto: di solito spinge troppo EQ e troppo Clarity su tracce aggressive.

---

## 2. Moduli — parametri e cosa fanno

### Equalizer (x2 nella catena: Equalizer 1 e 2)
- Filter Mode globale: **Analog** (IIR minimum phase, colore, nessun pre-ringing) /
  **Digital** (FIR linear phase, CPU alta, pre-ringing possibile sui bassi).
  In Digital: forma **Surgical** e controllo **Phase** per banda
  (0% = lineare, 100% = minima fase) — compromesso per ridurre pre-ringing.
- **Amount** 0-200% scala tutti i guadagni (100% = neutro).
- Gain −30/+15 dB, freq 20 Hz-20 kHz.
- Forme: Bell, **Proportional Q** (piu' tagli/alzi, piu' stringe: correzioni),
  Band Shelf (blocchi di frequenze), Shelf Analog/**Baxandall** (dolce, Q fisso)/
  **Vintage** (Pultec: boost + dip complementare)/Resonant; HP/LP Flat
  (Butterworth), Resonant, **Brickwall** (ellittico, Q fisso).
- Nodi di default: 20-100 Hz Baxandall Bass, 100 Hz-8 kHz Proportional Q,
  8-20 kHz Baxandall Treble.
- Alt+click = solo di una banda/regione (Q dell'alt-solo nelle Options).
- Options: **Soft Saturation** (se l'EQ satura, clip analogico invece di digitale),
  Extra Curves (phase/group delay: guardare il group delay sotto 100 Hz!).

### Dynamic EQ
- Analog/Digital, Stereo/M/S/L/R/T/S. Forme: Baxandall, Band Shelf, Peak Bell,
  Proportional Q. Gain −30/+15 dB.
- Direzione **UP/DOWN** per nodo: con gain negativo + DOWN = taglia solo quando supera
  la soglia (uso classico); con gain positivo + UP = alza solo quando supera
  (enfasi dinamica); DOWN con gain positivo = boost che si ritira sui picchi.
- Advanced: **Auto Scale** (attack/release scalati in base alla frequenza),
  Attack, Release, **Offset** (gain statico aggiuntivo).

### Dynamics (4 bande, compressore + limiter per banda)
- Detection: **Peak** (picchi), **Env** (media uniforme su tutte le frequenze, niente
  artefatti tipo RMS), **RMS**. Globale per tutte le bande.
- Ratio compressore **(10):1 … 30:1**, default 2:1. Ratio negative (mostrate 0.x:1)
  = **compressione upward** (alza cio' che sta SOTTO soglia).
- Ratio limiter (2.5):1 … 30:1, default 10:1; negative = **espansione upward**
  (alza cio' che supera la soglia: punch sui colpi). Non e' brickwall: a 30:1 puo'
  ancora sforare.
- Attack, Release, **Knee** (soft = naturale; hard = aggressivo), **Parallel** per
  banda (dry/wet = parallel compression dentro il modulo).
- Header: **Auto Gain** (make-up RMS per banda), **Adaptive Release** (release piu'
  corto sui transienti = meno pumping; piu' lungo sul sustain = meno distorsione),
  **Learn** (crossover automatici sui minimi dello spettro).
- **Detection Filter**: None / **Highpass** / **Tilt** (come il THRUST API: il low end
  pesa meno nel detector → il kick non fa pompare tutto il mix). **[uso] Sempre
  attivo in tekno**: HP 60-100 Hz sul detector o Tilt.
- Options: crossover **Analog/Digital/Hybrid** (Hybrid = IIR a ricostruzione
  perfetta, meno distorsione di fase), Crossover Q, **Look ahead 0-10 ms**.

### Vintage Compressor
- Compressore **feedback** con filtro di detection nel loop (HP, shelf, boost alti:
  decidi cosa lo fa lavorare). Modi: **Sharp** (transienti enfatizzati), **Balanced**,
  **Smooth** (piu' spesso e pieno). Threshold (soft knee in alcuni modi),
  Ratio, Attack, Release (release dei transienti; sul sustain e' molto piu' lungo:
  comportamento program-dependent), Gain, Auto Gain. Stereo o M/S.
- **[uso]** glue da bus: 1-2 dB GR, ratio 1.5-2:1, attack 10-30 ms, release sul groove.

### Vintage Limiter (Fairchild 670)
- Modi **Analog** (attacco veloce, release variabile, basso stretto e "thick"),
  **Tube** (attacco/release variabili, feedback morbido), **Modern** (vintage + IRC).
  Threshold, **Ceiling**, Link, True Peak, **Character** 0 (Fast) - 10 (Slow).
  Dopo la parte valvolare c'e' un IRC I che impedisce il clip.
- Manuale: ceiling −0.3 dB con dither; −0.6/−0.8 dB se si va in MP3/AAC.

### Vintage EQ (Pultec EQP-1A + MEQ-5)
- EQP-1A: Low freq **20/30/45/60/100 Hz** (45 aggiunto per il mastering), Low Boost e
  Low Cut **insieme** = boost sotto + dip sopra (il "trucco Pultec": sub pieno senza
  fango). High Boost 3/4/5/8/10/12/16 kHz con Q interattivo, High Cut shelf 5/10/20 kHz.
- MEQ-5: LM boost 200-1000 Hz, Mid cut 200 Hz-7 kHz, HM boost 1.5-5 kHz.
- **[uso]** tekno: Low 45 o 60 Hz boost +1..2 / cut +0.5..1 (stringe il kick sotto
  e pulisce 150-250); High boost 10-12 kHz +0.5..1 per aria.

### Vintage Tape (Studer A810)
- Speed **7.5 / 15 / 30 IPS** (30 = piu' esteso e pulito; 7.5 = piu' scuro, head bump
  piu' in basso). Input Drive (gain compensato internamente), **Bias** (negativo =
  piu' distorsione sugli alti; positivo = comincia a comprimere), **Harmonics**
  (armoniche pari), **Low Emphasis** (head bump fino a +10 dB), **High Emphasis**
  (default 4.0 = circa piatto).
- Sfasa il segnale: il Delta esagera la differenza percepita.

### Exciter (4 bande)
- Modi: **Analog** (dispari, transistor, grit), **Retro** (dispari che decadono
  lentamente), **Tape** (dispari brillanti), **Tube** (tonale, enfatizza gli attacchi),
  **Warm** (solo pari, decadono presto), **Triode** (mezzo circuito valvolare,
  sottile), **Dual Triode** (circuito intero, piu' drive e caldo).
- Per banda: Amount, Mix. **Oversampling** (anti-aliasing, attivarlo sempre sul
  master). **Post Filter** = high shelf sul solo wet per domare le armoniche alte.
- **[uso]** mai sulla banda sub (sporca il fondamentale); Tape/Retro su 2-8 kHz per
  presenza, Warm/Triode su 200-800 Hz per corpo. Mix 20-40%.

### Imager (4 bande)
- **Width** per banda: −100 = mono, positivo = piu' largo. **Amount** globale.
- **Stereoize** (solo se almeno una banda allarga): Mode I = Haas (copia ritardata
  del mid nel side), Mode II = piu' rispettoso dei transienti. Mono compatibile.
- **Recover Sides** (solo se almeno una banda stringe): rimette nel mid il side
  tolto, con gain e solo.
- Meter: vettorscopio (Polar Sample/Polar Level/Lissajous), **correlazione**
  (0..+1 normale; verso −1 = problemi di mono), bilanciamento stereo.
- Options: **Prevent Antiphase**.
- **[uso]** tekno/club: banda bassa (< 100-150 Hz) a **−100** (club = mono sotto;
  dati di 563 master techno/house: correlazione del sub mediana = 1.0, cioe' mono
  puro). Mid neutro, alti +5..+15 al massimo. Mai Stereoize su una traccia da club.

### Impact (4 bande, microdinamica)
- **Impact** per banda: positivo = espande la microdinamica (piu' aperto, punchy),
  negativo = comprime (piu' denso, glue). **Envelope** (ms o sincronizzato al tempo
  con **Sync**), **Auto-gain**, **Stereo Link** (unlink = agisce sugli elementi
  nella loro posizione stereo), Amount globale, Learn crossover.
- **[uso]** hardtek/tribe: banda 40-150 Hz Impact positivo leggero per il kick;
  alti leggermente negativi per ammorbidire hi-hat duri. Envelope sincronizzato
  a 1/16 sulle percussioni tribali.

### Low End Focus (20-300 Hz)
- Modi **Punchy** (risposta veloce, transienti) / **Smooth** (lenta, sustain).
- **Contrast**: positivo = piu' differenza tra contenuto forte e debole (toglie il
  fango "fuori fuoco", kick piu' pugno); negativo = sfuoca come saturazione/comp
  analogica. **Gain** = make-up della regione. Action region 20-300 Hz con solo.
- **[uso]** kick+basso che si impastano: Punchy, regione 40-200 Hz, Contrast +15..+35.

### Clarity (novita' v11)
- Centinaia di bande: contorna lo spettro verso rumore "piatto" adattivamente;
  doma risonanze e smaschera il fondo. Test ciechi iZotope: aumenta la loudness
  percepita a pari LUFS integrati.
- **Amount** (a 100 max ±6 dB), **Tilt** in dB/oct (0 = rosa; +3 = bianco,
  piu' brillante; −3 = marrone, piu' scuro), Attack, Release (ms), action region
  **300 Hz-20 kHz**. Stereo, M/S o T/S.
- **[uso]** mix opachi: 20-40 di Amount. Su acid/hardtek gia' aggressivi rischia di
  indurire: Tilt −1..−2 o limitare la regione a 300 Hz-6 kHz; controllare col Delta.

### Stabilizer (EQ adattivo)
- **Target** di bilanciamento tonale (anche "Assistant" da reference; salvabile come
  preset di modulo). **Mode**: **Shape** (boost e tagli, loudness-neutro) /
  **Cut** (solo tagli sulle risonanze oltre il limite superiore del target).
- Amount (a 100 fino a 9 dB), **Speed**, **Smoothing** (100 = 3-4 filtri larghi,
  0 = tantissimi filtri stretti), **Sensitivity** (0 = solo le risonanze estreme,
  100 = qualunque deviazione), **Tame Transients**, Amount separati
  **Low < 100 Hz / Mid 100 Hz-5.6 kHz / High > 5.6 kHz**.
- **[uso] acid**: il 303 con risonanza che spazza crea picchi che si spostano —
  Stabilizer in **Cut**, Sensitivity 40-60, Speed medio-alto, Low a 0 (non toccare
  kick/sub), Mid 60-100. Molto meglio di un EQ statico.

### Spectral Shaper
- Riduzione spettrale ad alta risoluzione (tipo "soothe"): **Mode** Low/Medium/High
  (intensita'), Amount, **Tone** (tilt: + brillante, − scuro), Attack, Release,
  action region su tutto lo spettro, Learn. Stereo, M/S, T/S.
- **[uso]** asprezza 2-6 kHz di kick distorti/hat/303: regione 2-8 kHz, Mode Low,
  Amount basso, attack veloce. In T/S solo sul Sustain per non smussare i colpi.

### Master Rebalance
- AI che isola **Vocals / Bass / Drums** (uno alla volta) e ne cambia il livello
  nel mix stereo. Spettro blu = focus, grigio = residuo.
- **[uso]** kick troppo basso nel mix stereo senza avere gli stem: Drums +1..+2 dB.
  Ascoltare bene: su suoni sintetici estremi la classificazione sbaglia.

### Match EQ
- EQ lineare fino a 8000+ bande. Cattura **Reference** (dorato; salvato nel preset)
  e **Apply To** (blu; non salvato), poi **Smoothing** e **Amount**.
  Manuale: tenere Amount **sotto 50%** e alzare lo Smoothing: si copia la forma
  generale, non ogni picco. Cutoff low/high per limitare la zona (es. solo i bassi).

### Maximizer (limiter finale, NON multibanda)
- Modi IRC:
  - **IRC LL** (Low Latency): IRC 1 a bassa latenza, CPU minima.
  - **IRC 1**: veloce sui transienti (no pumping), lento sui bassi tenuti (no distorsione).
  - **IRC 2**: come IRC 1 ma preserva di piu' i transienti.
  - **IRC 3**: il piu' aggressivo, modello psicoacustico; latenza alta (sopra 48 kHz
    puo' non girare in real time). Stili: **Clipping** (massima loudness, colora),
    **Crisp** (preferisce distorsione a pumping), **Balanced** (trasparente),
    **Pumping** (legacy, release libero).
  - **IRC 4**: limita le bande che causano i picchi (decine di bande
    psicoacustiche), meno pumping e intermodulazione; il piu' pesante in CPU.
    Stili: **Classic**, **Modern**, **Transient** (massima preservazione transienti).
- **Gain** (ex Threshold, si alza), **Output Level** (ex Ceiling), link Gain/Output
  (ascolto senza bias "piu' forte = meglio"), **True Peak** (le inter-sample possono
  superare il campione di oltre 3 dB), **Character** 0 (Clipping) - 10 (Very Slow).
- **Learn Input Gain** + **Target LUFS**: ascolta 5 s e imposta la Gain.
  Manuale: non usarlo per la compliance loudness.
- Secondari:
  - **Upward Compress** (dB = gain massimo sulle parti deboli; parallel compression
    level-matched: i picchi a 0 dBFS restano allo stesso livello; prima dell'IRC).
  - **Soft Clip** (prima dell'IRC, oversampling 4x, Amount = dry/wet; a 100% clippa
    pieno a 0 dBFS): **Light** satura da −3 dBFS, **Moderate** da −9, **Heavy** da −30.
  - **Transient Emphasis** (Amount): scolpisce i transienti prima del limiter.
  - **Stereo Independence** Transient/Sustain (0% = link come il vecchio Stereo
    Unlink a 0): piu' alto = piu' loud ma immagine piu' stretta.
- Viste: spettro, waveform + gain trace (giu' = limiter, su = upward), GR L/R.

### Dither (mothership + Maximizer)
- Va **dopo tutto**, ultimo insert, post-fader; disattivare il dither dell'export
  della DAW (niente doppio dither). Bit depth 24/20/16/12/8.
- **MBIT+**. Amount: **Strong / Medium (consigliato) / Low / Off**. Harmonic
  Suppression (solo con Amount Off). **Noise Shaping** Off…Max (~14 dB di
  riduzione percepita). Auto-Blanking (silenzio > 0.7 s). Limit Peaks. Bit Meter.
- **DC Offset**: meter + HP a **1 Hz** prima del Maximizer/Vintage Limiter.
- **[uso]** export 24 bit (club/Beatport/distributore): dither non necessario da 32
  float a 24 bit in pratica, ma innocuo; export 16 bit (CD/Bandcamp 16): Medium +
  noise shaping moderato.

### Codec Preview
- MP3 (LAME) / AAC (Fraunhofer), CBR 96-320 kbps, **Solo Artifacts** (ascolti cosa
  toglie il codec). Sopra 48 kHz ricampiona in tempo reale.
- Manuale: per formati lossy lasciare **−1 / −1.5 dB** di headroom (il codec alza i
  picchi). Mettere Ozone ultimo sul master per sentire cio' che verra' esportato.

### Referencing
- Fino a **10 reference** (wav/aif/mp3/AAC/FLAC), loop segments auto (A/B/C...),
  Gain di playback (**abbassarlo a pari loudness** prima di confrontare), "Show
  Reference Spectrum" in tutti gli analizzatori, "Replace Input with Reference".

### Preset
- Fabbrica: `C:\Program Files\iZotope\Ozone\Presets\`
- Utente: `C:\Users\<utente>\Documents\iZotope\Ozone\User Presets\`
- Preset globali (catena intera) e di modulo; si puo' impostare un preset come
  Default per le nuove istanze. **[uso]** salvare li' le catene LIVEMIND per genere
  (vedi sezione 4) cosi' si richiamano con un click.

---

## 3. Flusso di mastering in Ozone (metodo LIVEMIND)

1. Mix con ~−6 dBFS di picco sul master, niente limiter sul mix. Export o Ozone
   direttamente sul Main track (ultimo device, dopo tutto).
2. Caricare 2-3 reference del genere nel Referencing, gain-matchati.
3. (Opz.) Master Assistant con target da reference → studiare cosa propone.
4. Costruire/rifinire la catena nell'ordine: **correttivo → tono → dinamica →
   stereo → colore → loudness**. Ogni modulo: Delta + Gain Match + bypass.
5. Maximizer ultimo; Dither/Codec come controllo finale.
6. Verifica con le misure di LIVEMIND (`livemind.audio.loopback`,
   `livemind.audio.reference`): LUFS del drop, true peak, bande, mono sotto 120 Hz.
7. Ascolto in mono, a basso volume, e sul sistema piu' scarso disponibile.

Ordine tipico (club tekno):
`EQ1 correttivo (Analog, M/S) → Dynamic EQ / Spectral Shaper (asprezze) →
Low End Focus → Dynamics o Vintage Compressor (glue, detection HP) → Impact →
Imager (mono sotto 120 Hz) → Exciter / Vintage Tape (colore) → EQ2 tono finale →
Maximizer (Soft Clip + IRC)`

Regole:
- Ogni modulo deve guadagnarsi il posto: se col bypass non si sente/misura
  differenza utile, via.
- Guadagno di un modulo in piu' ≈ 0 dB (Auto Gain / gain match) finche' non si
  arriva al Maximizer: l'unico punto dove si "fa volume".
- Limiter: mirare a 2-4 dB di GR sui picchi del drop; oltre, prima clippare
  (Soft Clip) o sistemare il mix (kick troppo sporgente = clip sul kick nel mix).

---

## 4. Catene per genere (punto di partenza)

Valori numerici codificati in `livemind/mastering/ozone_chains.py`
(`chain_for(genere, destinazione)`), qui la logica:

- **hardtek** (170-190 BPM, kick distorto dominante): la loudness la fa il kick.
  Low End Focus Punchy leggero, Dynamic EQ su 2.5-4 kHz (asprezza del kick),
  compressione minima (detection HP 100 Hz), Imager mono < 120 Hz,
  Maximizer **IRC 3 Crisp** o IRC 4 Transient, Soft Clip Moderate 30-50%,
  Transient Emphasis 10-20. Drop short-term **−6.5 … −5 LUFS**.
- **tekno_tribe** (150-170 BPM, percussioni tribali): preservare i transienti delle
  percussioni. Impact positivo sui medi (bongo/tom), Vintage Compressor Sharp
  leggerissimo, IRC 4 **Transient**, Soft Clip Light. Drop **−7.5 … −6 LUFS**.
- **acid** (135-155 BPM, 303 in primo piano): il nemico e' la risonanza mobile.
  Stabilizer **Cut** (Low 0), Spectral Shaper sul Sustain 1-5 kHz, Exciter Tube sul
  corpo del 303 con mix basso, IRC 4 **Modern**. Drop **−8 … −6.5 LUFS**.
- **hardflor** (hardfloor/hard tekno 160-175 BPM): tra hardtek e tribe; kick lungo e
  rullante marcato. Low End Focus Punchy, Vintage Limiter Analog leggero come
  "glue grasso" prima del Maximizer, IRC 3 Balanced. Drop **−7 … −5.5 LUFS**.

Destinazione **streaming**: stessa catena, Maximizer meno spinto (integrato
~−9/−10 LUFS e' comunque normalizzato: spingere oltre perde solo punch), True Peak
ON a **−1 dBTP** (−2 dBTP se la traccia e' molto forte: i codec aggiungono picchi).
Destinazione **club** (WAV 24 bit per DJ/USB): True Peak ON, Output −1.0 dBTP come
regola LIVEMIND. Nota: i master techno pubblicati spesso superano 0 dBTP
(misure su 563 tracce lossless: mediana del TP tra +0.5 e +1.2 dBTP) — e' prassi,
non un obiettivo: il −1 dBTP costa ~0 di loudness percepita.

Tutti questi numeri sono **ipotesi da validare** contro `references/<genere>/`
dell'utente con `python -m livemind.audio.reference`.
