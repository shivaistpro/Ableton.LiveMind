# Mastering — tecniche complete

Scopo del mastering: traduzione (suona bene ovunque), coerenza (tra tracce di un
release), loudness adeguata alla destinazione, controllo qualita' tecnico.
Il mastering non ripara un mix: se il problema e' di un singolo elemento, si torna
al mix (o allo stem mastering).

---

## 1. Preparazione del mix (checklist di ingresso)
- Picco del mix **−6…−3 dBFS**, niente limiter/clipper sul master del mix
  (eventualmente un bus comp "da mix" leggero se fa parte del suono).
- Export **WAV/AIFF 32-bit float** (o 24-bit) alla sample rate del progetto; niente
  dither, niente normalizzazione.
- 1-2 s di silenzio prima/dopo; code dei riverberi non tagliate.
- Controllo: fase in mono, DC offset, click/pop, inter-sample over, clip interni.
- Reference del genere pronte, in lossless, **a pari loudness** durante il confronto.

## 2. Ascolto e misure
- Monitor calibrati e volume costante (es. ~79-83 dB SPL); ascolto anche a basso
  volume, mono, cuffie, sistema piccolo, auto.
- Meter indispensabili: **LUFS** (momentary 400 ms, short-term 3 s, integrated),
  **true peak (dBTP)**, **LRA**, **PLR** (peak-to-loudness = TP − LUFS integ.),
  analizzatore di spettro con tilt 3 dB/oct, correlazione/vettorscopio,
  stereo width per banda.
- In elettronica si giudica la **sezione del drop** (short-term), non l'integrato di
  tutto il brano: intro/breakdown abbassano l'integrato.

## 3. Loudness — destinazioni (dati 2026)
| Destinazione | Target di normalizzazione | True peak consigliato |
|---|---|---|
| Spotify | −14 LUFS (Loud −11, Quiet −19) | −1 dBTP; −2 se il master e' molto forte |
| Apple Music | −16 LUFS (alza anche i brani deboli) | −1 dBTP |
| YouTube / Tidal | −14 LUFS (non alzano i brani deboli) | −1 dBTP |
| Amazon Music | −14 LUFS | −2 dBTP |
| Bandcamp / Beatport / file per DJ | nessuna normalizzazione | −1 dBTP (regola LIVEMIND) |
| Broadcast EBU R128 | −23 LUFS | −1 dBTP |

Dati reali (563 master techno/house lossless): LUFS integrato mediano
House −11.4, Tech House −12.1, Groove Techno −10.9, Melodic −12.3,
Peak-time −11.0, **Hard Techno −10.3**; kick fondamentale 50-62 Hz
(hard techno mediana 62.5 Hz); correlazione del sub = 1.0 (mono);
energia 60-250 Hz > 20-60 Hz in quasi tutti gli stili.

Conseguenze pratiche:
- Master "club" della tekno dura: drop short-term tipicamente −7…−5 LUFS.
- Sulle piattaforme una traccia a −6 LUFS viene abbassata di ~8 dB: se e'
  schiacciata suonera' piu' piccola di una a −9 con dinamica. Valutare un
  **master separato per lo streaming** (stessa catena, meno limiting).
- **PLR** del drop: sotto ~6 dB il kick perde impatto; tekno dura sta spesso a 6-8.

## 4. Catena del segnale — ordine e perche'
Ordine di riferimento (ogni blocco facoltativo):
1. **Correttivo**: HP subsonico (20-30 Hz, pendenza dolce o lineare), tagli stretti
   di risonanze, de-ess/dynamic EQ.
2. **Tonale**: shelf ampi/Baxandall/Pultec, EQ M/S.
3. **Dinamica**: bus comp (glue) → eventuale multibanda → espansione/transient.
4. **Stereo**: mono sotto 100-150 Hz, larghezza dei medio-alti.
5. **Colore**: saturazione/tape/valvola (armoniche = loudness percepita).
6. **Loudness**: clipper → limiter true-peak.
7. **Uscita**: SRC (se serve) → dither (solo se riduci la bit depth) → export.
Variante: EQ tonale anche **dopo** il comp (il comp cambia il bilanciamento).

## 5. EQ in mastering
- Mosse piccole (±0.5…2 dB), Q larghi; tagli stretti solo per risonanze reali.
- **Minimum phase** (analog): suono piu' naturale sui transienti, sfasamento vicino
  alla frequenza. **Linear phase**: nessuno sfasamento ma **pre-ringing** (sbavatura
  prima del colpo) soprattutto con filtri ripidi sui bassi: sul kick si sente.
  Scelta: linear phase per M/S e tagli bassi ripidi se non si sente pre-ringing;
  altrimenti analog.
- **Mid/Side EQ**: Side HP 100-200 Hz (bassi mono), boost alti sul Side per aria,
  taglio 200-500 Hz sul Side per pulire, presenza sul Mid (voce/lead).
- **Tilt EQ**: un unico controllo per bilanciare scuro/brillante.
- **Pultec trick**: boost e cut sulla stessa frequenza bassa (sotto pieno, dip sopra).
- **Dynamic EQ** vs multibanda: dinamico = una zona stretta interviene solo quando
  eccede (harshness del lead, basso che rimbomba su certe note); multibanda = bande
  larghe con crossover.
- **Resonance suppressor** (Spectral Shaper, soothe, Stabilizer Cut): per risonanze
  mobili (303, lead acidi, distorsioni).
- **Match EQ**: copiare la curva media di un reference, amount < 50%, smoothing alto.

## 6. Dinamica in mastering (vedi `compression.md` per i tipi)
- **Bus/glue compression**: ratio 1.5-2:1 (anche 1.2:1), attack 10-30 ms (lascia
  passare il transiente), release auto o sul tempo, GR 1-2 dB, detection HP
  60-120 Hz (il kick non fa pompare tutto).
- **Multibanda**: 3-4 bande; tipicamente low 1-2 dB per stabilizzare il basso,
  mid quasi niente, high per domare hat/harshness. Crossover lontani da elementi
  chiave (non a 60 Hz sul fondamentale del kick). Attenzione alla distorsione di
  fase dei crossover (preferire linear/hybrid).
- **Parallel compression** in mastering: 10-30% di un comp pesante mescolato al dry
  (in Ozone: Parallel nel Dynamics, oppure Upward Compress del Maximizer).
- **Upward compression**: alza i dettagli bassi senza toccare i picchi (densita'
  trasparente). **Upward expansion**: alza i picchi (punch su mix piatti).
- **Transient shaping** (Impact, Transient Emphasis, transient shaper): riportare
  punch dopo il limiting o prima per compensarlo.
- **Stem/element-aware**: Stem Focus/Master Rebalance per cambiare kick o basso nel
  mix stereo quando non ci sono stem.

## 7. Saturazione e colore
- Armoniche = piu' loudness percepita a parita' di picco, piu' definizione del basso
  sui piccoli speaker (armoniche del sub nella zona 100-300 Hz).
- Pari (valvola/warm) = rotondo, dispari (transistor/tape/clip) = aggressivo.
- **Tape**: head bump, compressione morbida degli alti, glue.
- Parallelo o multibanda per non sporcare il sub; oversampling sempre.
- Nella tekno dura la distorsione e' gia' nel mix: in mastering colore minimo.

## 8. Stereo
- Bassi **mono** sotto 100-150 Hz (club = sistemi mono o quasi sui sub; vinile).
- Correlazione media 0…+1; negativa = cancellazioni in mono.
- Allargare solo i medio-alti, poco; niente Haas/Stereoize su master da club.
- Controllo finale in mono: il kick e il basso NON devono perdere livello.

## 9. Clipping e limiting (la loudness)
- **Clipper**: taglia istantaneamente i picchi brevi (transienti del kick/rullante):
  0.5-2 dB (fino a 3-4 in elettronica dura) sono spesso invisibili all'orecchio e
  tolgono lavoro al limiter. Soft clip = armoniche morbide; hard clip = piu'
  trasparente se poco, piu' "crunch" se tanto. **Oversampling** per ridurre aliasing.
- Ordine comune: **clip → limit**. Il limiter poi fa 1-3 dB di GR medio.
- **Limiter**: lookahead, attack rapidissimo, release program-dependent;
  stili da scegliere sul materiale (trasparente vs punchy vs pompa).
  Due limiter in serie (1-2 dB ciascuno) = meno artefatti di uno solo da 5 dB.
- **True peak**: limiter con oversampling (ISP-aware) → ceiling −1 dBTP
  (−0.3 dB solo se non ci saranno codec lossy e si accetta il rischio).
- "Clip to zero": clippare il mix a 0 dBFS con clipper oversampled e usare il
  limiter solo per la compliance TP — tecnica diffusa in EDM/hard.
- Segnali di troppo limiting: kick che si accorcia/perde basso, hat che pompano con
  il kick, distorsione sul basso tenuto, breakdown piu' forte del drop.

## 10. Uscita: SRC, dither, formati
- Lavorare alla sample rate del mix; SRC di alta qualita' solo alla fine.
- **Dither** solo quando si riduce la bit depth (es. 24→16): una volta, alla fine,
  con noise shaping moderato. 32-float → 24-bit: dither irrilevante.
- Formati: WAV 24-bit 44.1/48 kHz per DJ/Beatport/distributori; 16-bit 44.1 per CD;
  MP3 320/AAC 256 solo come copie (verificare con codec preview: picchi +0.5…1.5 dB).
- **Vinile**: sibilanti e alti controllati, bassi mono sotto ~150 Hz, niente fuori
  fase, loudness moderata (tempo per lato inversamente legato al livello dei bassi).

## 11. Tecniche avanzate
- **Stem mastering**: 4-8 stem (kick, bass, drums, synth, fx, vox) → piu'
  controllo; processare stem e bus stereo insieme.
- **Mid/Side compression**: comprimere solo il Side per stabilizzare la larghezza,
  o solo il Mid per il punch centrale.
- **Sidechain nel master**: vietato in genere (pompa tutto); ok solo se voluto.
- **Serial processing**: tanti processori leggeri > uno pesante.
- **Automazione in mastering**: +0.5 dB sul drop, EQ diverso nel breakdown,
  limiter che lavora meno nell'intro: il master non deve essere statico.
- **Album/EP**: stessa loudness percepita tra tracce (non stesso LUFS), transizioni,
  code, ordine; stessa catena base con piccole varianti.
- **DJ-friendly**: intro/outro con kick pulito e bassi presenti (mix in consolle),
  griglia costante, niente fade in/out sul primo/ultimo beat.

## 12. Controllo qualita' finale (QC)
- [ ] True peak ≤ target in tutto il brano (non solo nel drop)
- [ ] Nessun clip/over, nessun click all'inizio/fine, silenzi puliti
- [ ] Mono check: kick e basso stabili, correlazione > 0 nei drop
- [ ] LUFS del drop e integrato nel range del genere (confronto con reference)
- [ ] Bilanciamento tonale vicino alle reference (sub/bass/mid/high)
- [ ] Ascolto completo dall'inizio alla fine (errori nelle sezioni meno ascoltate)
- [ ] Codec preview se va in streaming
- [ ] Metadati/ISRC se e' un release; nome file chiaro (Artista - Titolo (Master) 24-44.1)
