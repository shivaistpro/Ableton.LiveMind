# Compressione — tutti i tipi e le tecniche

## 1. Parametri (cosa fanno davvero)
- **Threshold**: livello oltre cui interviene (downward) o sotto cui (upward).
- **Ratio**: 1.5-2:1 glue, 3-4:1 controllo, 8-10:1 aggressivo, >10:1 = limiting.
  Ratio < 1 (o negative in Ozone) = espansione / compressione upward.
- **Attack**: lento (10-30 ms+) lascia passare il transiente = piu' punch;
  veloce (< 1-3 ms) mangia il transiente = piu' controllo, suono piu' "morto".
- **Release**: veloce = piu' loudness ma pumping e distorsione sui bassi (un release
  piu' corto del periodo della fondamentale distorce: 50 Hz = 20 ms);
  lento = piu' naturale ma puo' non recuperare tra i colpi.
  **Sincronizzato al tempo**: il release deve far "respirare" il comp tra un kick e
  l'altro (a 175 BPM un 1/4 = 343 ms → release ~100-250 ms).
- **Knee**: soft = graduale, musicale; hard = netto, aggressivo.
- **Detection**: Peak (reagisce ai picchi) vs RMS (alla media, piu' "musicale");
  **feedforward** (detector sull'ingresso: preciso, moderno) vs **feedback**
  (detector sull'uscita: si auto-corregge, piu' morbido e colorato, vintage).
- **Lookahead**: vede i picchi in anticipo (latenza); essenziale nei limiter.
- **Sidechain filter / detection filter**: HP 60-150 Hz per non far pompare il kick
  (o tilt tipo THRUST); band-pass per de-esser o compressione di una sola zona.
- **Stereo link**: link = immagine stabile; unlink = piu' GR ma l'immagine si sposta.
- **Mix/parallel**: dry/wet interno.
- **Make-up / auto gain**: confrontare SEMPRE a pari livello.

## 2. Tipi di circuito (e le loro emulazioni)
| Tipo | Come funziona | Tempi | Carattere | Classici | Uso tipico |
|---|---|---|---|---|---|
| **VCA** | amplificatore controllato in tensione | precisi, rapidi, regolabili | pulito, punchy, preciso | SSL G bus, API 2500, dbx 160 | master bus, drum bus, glue |
| **FET** | transistor a effetto di campo, spesso feedback | attacco rapidissimo (µs) | aggressivo, colorato, "davanti" | UREI 1176 | drums, bassi, room aggressive, parallel "all buttons" |
| **Opto** | LED + fotoresistenza | attacco lento, release a due stadi program-dependent | morbido, liscio | LA-2A, LA-3A | voci, bassi, pad, livellamento |
| **Vari-mu** | valvola con bias variabile | lenti, dolcissimi, ratio che cresce col livello | colla, spessore, armoniche | Fairchild 670, Manley Vari-Mu | mix bus, mastering glue |
| **Diode bridge** | ponte di diodi | medio-veloce | grana, distorsione ricca | Neve 2254/33609 | bus, colore |
| **PWM** | modulazione a larghezza d'impulso | veloce, pulito | trasparente con carattere | Pye, Cranesong | bus, mastering |
| **Digitale** | algoritmo | qualsiasi, lookahead, zero colore | trasparente o modellato | Pro-C 2, Ableton Compressor | tutto |

In Ableton: **Glue Compressor** (VCA stile SSL bus: ratio 2/4/10, attack 0.01-30 ms,
release 0.1-1.2 s + Auto, Soft Clip, Range), **Compressor** (Peak/RMS/Expand,
lookahead 0/1/10 ms, sidechain EQ, modo **Expand**), **Multiband Dynamics**
(3 bande, above/below, upward/downward compress/expand), **Drum Buss**
(comp fisso + drive + transients + boom), **Limiter** (12.1+: Soft Clip, True Peak,
Mid/Side, Maximize), **Gate**. In Ozone: Dynamics, Vintage Compressor
(feedback), Vintage Limiter (Fairchild), Impact, Maximizer.

## 3. Famiglie di dinamica
- **Downward compression**: abbassa cio' che supera la soglia (standard).
- **Upward compression**: alza cio' che sta sotto (dettaglio, densita', trasparente).
- **Downward expansion / gate**: abbassa cio' che sta sotto (pulizia, rientri,
  code corte). Gate con **hold** e **hysteresis** per non "chattering".
- **Upward expansion**: alza cio' che supera (punch, ridare vita a mix schiacciati).
- **Limiting**: ratio infinita, lookahead, ceiling.
- **Clipping**: limitazione istantanea della forma d'onda (soft/hard).
- **Transient shaping**: agisce sull'inviluppo, non sul livello assoluto
  (attack/sustain indipendenti dal livello di ingresso).
- **De-essing**: compressione su banda sibilante (4-10 kHz), anche per hat duri.
- **Multibanda**: compressione per bande con crossover.
- **Dynamic EQ**: una campana che si muove col livello (piu' chirurgico).
- **Spectral/resonance compression**: centinaia di bande (soothe, Spectral Shaper).

## 4. Tecniche
### Parallel (New York) compression
Send (o rack a due catene) a un comp pesante: ratio 8-20:1, attack rapido, release
medio, 10-20 dB di GR, spesso saturato ed EQ-ato (+alti, +bassi "smile"); mescolato
sotto al dry. Densita' e sustain senza perdere transienti. Su drum bus tekno:
parallel con distorsione (Drum Buss/Roar/Saturator) = muro ritmico.

### Serial compression
Due o tre comp leggeri in fila (es. FET veloce per i picchi → opto lento per il
livello) invece di uno pesante: meno artefatti.

### Sidechain
- **Ducking** classico: basso/pad/synth compressi dal kick (attack 0-5 ms,
  release sul groove, ratio 4:1+, 3-8 dB). Alternativa piu' precisa: volume
  shaper / LFO Tool / Auto Pan ritmico, o **sidechain multibanda** (solo < 150 Hz
  del basso ducka sul kick: il resto del basso resta).
- **Ghost/trigger kick**: traccia muta con un kick fisso a 4/4 come sorgente del
  sidechain → ducking costante anche nei breakdown.
- **Sidechain sui return**: riverbero/delay duckati dal dry o dal kick → effetto
  presente ma non impasta (vedi `return-fx.md`).
- **Key filtering**: sidechain EQ che isola il kick (40-100 Hz) nella sorgente.
- **Sidechain gate**: pad/rumore "trancegate" aperto dal ritmo di un'altra traccia.

### Glue su gruppi
Drum bus: VCA 2:1-4:1, attack 10-30 ms, release auto o 100-300 ms, 2-4 dB.
Tekno: il kick spesso fuori dal drum bus (o sidechain HP nel detector) per non
far pompare le percussioni.

### M/S e L/R
Comprimere il Mid per il punch centrale, il Side per stabilizzare la larghezza.

### Compressione per il groove
Attack/release che creano un "respiro" a tempo = swing percepito. In tribe tekno:
comp FET sulle percussioni con release 1/16 fa "camminare" il pattern.

## 5. Settaggi di partenza per sorgente (tekno/hard)
| Sorgente | Tipo | Ratio | Attack | Release | GR |
|---|---|---|---|---|---|
| Kick (dopo distorsione) | FET/VCA o clipper | 4:1 / clip | 10-30 ms | 50-100 ms | 2-4 dB o clip 1-3 dB |
| Basso rolling | opto/VCA + sidechain kick | 3-4:1 | 5-20 ms | auto | 3-6 dB |
| 303 acid | opto o FET leggero, + dynamic EQ | 2-4:1 | 5-15 ms | 50-150 ms | 2-4 dB |
| Hat/percussioni | FET veloce o transient shaper | 4:1 | 1-5 ms | 30-80 ms | 2-3 dB |
| Percussioni tribali (tom/bongo) | FET + parallel | 4-8:1 | 5-15 ms | 1/16 sync | 3-6 dB |
| Drum bus | VCA (Glue) | 2-4:1 | 10-30 ms | auto | 2-4 dB |
| Mix bus | VCA/vari-mu | 1.5-2:1 | 10-30 ms | auto | 1-2 dB |
| Parallel NY | FET/VCA estremo | 10-20:1 | 0.1-1 ms | 50-100 ms | 10-20 dB (mix 10-30%) |
