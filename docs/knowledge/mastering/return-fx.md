# Return track — effetti e trucchi di mixing

## 0. Regole base (Ableton)
- Send della traccia → return. **Pre/Post** per ogni return: Post = dopo
  volume/pan/attivazione (standard); **Pre** = il send non segue il fader → "throw":
  abbassi il fader della traccia e resta solo l'effetto.
- I send dei return verso altri return sono **disattivati di default** (rischio
  feedback): tasto destro sul send → *Enable Send*. Permette catene return→return
  e loop di feedback controllati (sempre con Limiter sul return!).
- Return al 100% wet; mai il dry nel return (fase/raddoppio).
- **EQ sui return** (trucco Abbey Road): HP 150-600 Hz e LP 6-10 kHz sul riverbero
  = spazio senza fango e senza sibilanti.
- **Bassi mono sui return**: Utility Bass Mono (o HP) — un riverbero stereo sotto
  150 Hz distrugge il mono del club.
- Gestire i return con i **gruppi**: Audio From/To e "Sends Only" per routare
  un gruppo intero su un return dedicato.
- Automatizzare il **send**, non il wet del device: e' piu' pulito.

## 1. Riverberi
- **Tipi**: room (corto, coesione), plate (brillante, denso, su snare/voci),
  hall (grande, lungo), chamber, spring (dub!), convolution (spazi reali),
  shimmer (pitch +12 nel feedback), algoritmici "space" (Valhalla/Hybrid Reverb).
- **Pre-delay**: separa il dry dal riverbero (chiarezza). Sincronizzato: 1/64-1/32
  (a 175 BPM: 1/64 ≈ 21 ms, 1/32 ≈ 43 ms). Formula in `delay_ms()`.
- **Decay a tempo**: la coda deve morire prima del colpo successivo (groove) o
  essere volutamente un "pad" (breakdown).
- **Riverbero duckato**: comp sul return con sidechain dalla sorgente dry (o dal
  kick): la coda "fiorisce" nelle pause. Fondamentale nella tekno veloce.
- **Gated reverb**: riverbero grande + Gate (o comp estremo) → coda tagliata a tempo
  (anni '80, snare giganti, clap tekno).
- **Reverse reverb**: resample del return, reverse, fade: "risucchio" prima del colpo.
- **Freeze / infinite**: decay max o freeze durante i break → pad da un solo colpo.
- **Riverbero distorto**: Saturator/Roar DOPO il riverbero = coda sporca rave;
  PRIMA = attacco sporco e coda pulita.
- **Riverbero filtrato in automazione**: Auto Filter LP che si apre nel build.
- **Short room su percussioni**: 0.3-0.8 s, HP 300 Hz → percussioni "nello stesso
  posto".

## 2. Delay
- Tempi a nota (vedi tabella/`delay_ms`): 1/4, 1/8, 1/16, puntati (×1.5 —
  1/8d = 3/16), terzine (×2/3). **Dotted 1/8** = il classico "galoppo".
- **Ping-pong**: alterna L/R (attenzione al mono: in club collassa).
- **Dub delay** (tekno/dub): feedback 50-80%, filtro nel loop (HP 200-400 Hz +
  LP 2-4 kHz: ogni ripetizione piu' scura/sottile), saturazione nel loop
  (Echo di Ableton: Character → Noise/Wobble/Drive; o Saturator dopo),
  **throw** con send in Pre sull'ultima sillaba/colpo, poi automazione del feedback
  fino all'auto-oscillazione e taglio.
- **Tape delay**: wow/flutter, degradazione, spring nel loop.
- **Haas**: 10-30 ms su un lato = larghezza (non mono-compatibile: mai sui bassi).
- **Delay → reverb** (return delay che manda nel return reverb): ripetizioni che si
  sciolgono nello spazio.
- **Delay duckato** (sidechain dal dry): ripetizioni solo nelle pause.
- **Modulated delay** corto (chorus/flanger) per larghezza su pad e hat.
- **Grain Delay / Beat Repeat** su return: glitch, stutter, pitch.

## 3. Return di dinamica e colore (parallel)
- **Parallel compression bus** (NY): drum → return con comp pesante (vedi
  `compression.md`), EQ "smile" dopo. Send pre o post a gusto.
- **Parallel saturation/distortion**: Saturator/Roar/Drum Buss al 100% wet su return,
  HP 200 Hz → aggiunge grinta e armoniche senza sporcare il sub (tecnica chiave per
  kick e bassi nella tekno dura).
- **Crush/bitcrush return**: Redux (downsample/bit) per texture sporche, dosato.
- **Exciter return**: HP 3-5 kHz + saturazione = aria/presenza parallela.
- **Sub/octave return**: pitch −12 filtrato, per ispessire un basso (attento al mono).

## 4. Return di modulazione e spazio
- **Chorus/ensemble** 100% wet su pad/lead: larghezza controllabile.
- **Flanger/Phaser** con feedback alto, automatizzati nei build.
- **Auto Pan** ritmico (tremolo a tempo) sul return = movimento senza toccare il dry.
- **Resonator/Spectral Resonator/Corpus** su percussioni: tonalizzare i colpi
  (percussioni "accordate" tribali).
- **Vocoder/Spectral** tra return: creativita' pura.

## 5. Tecniche specifiche tekno / rave
- **Rumble kick** (techno/hard techno): kick → send (post) → return con: riverbero
  lungo (2-6 s, pre-delay 0) → saturazione/distorsione → **sidechain dal kick**
  (ducking pesante) → **LP 150-250 Hz** + HP 30-40 Hz, mono. Il "rimbombo" tra i
  kick: fondamentale nell'hardtek/hard techno. Accordare la coda alla tonalita'.
- **Tribe**: percussioni su un return **short room** comune + un return **delay 1/16
  terzinato** a basso volume → poliritmia percepita.
- **Acid**: 303 su return **delay 3/16 dub** filtrato + riverbero plate corto
  duckato; automazione del send durante le aperture del cutoff.
- **Build/transizioni**: return con riverbero enorme (decay 10-15 s) + automazione
  del send a 100% sull'ultimo colpo prima del break; **reverse reverb** del colpo
  prima del drop; **feedback loop** delay→reverb controllato con limiter.
- **Throw FX**: send in Pre + automazione a scalino su una frase = effetto "eco
  che rimane" quando la traccia sparisce.
- **Mono nei club**: ogni return con Utility (Bass Mono 120-150 Hz) e correlazione
  controllata; i trucchi stereo solo sopra 300-500 Hz.

## 6. Livelli e gain staging dei return
- I return sommati fanno crescere il master: controllare il picco del mix (−6 dBFS).
- Un effetto "si sente" quando lo togli: regolare il send finche' manca se spento.
- Riverbero nei drop tekno: poco (masking); nei breakdown: tanto.
- Limiter/Clipper di sicurezza sui return con feedback alto.

## 7. Tabella delay (ms) — formula: 1/4 = 60000 / BPM
| BPM | 1/4 | 1/8 | 1/8d | 1/16 | 1/8t | 1/16t | 1/32 | 1/64 |
|---|---|---|---|---|---|---|---|---|
| 135 | 444.4 | 222.2 | 333.3 | 111.1 | 148.1 | 74.1 | 55.6 | 27.8 |
| 145 | 413.8 | 206.9 | 310.3 | 103.4 | 137.9 | 69.0 | 51.7 | 25.9 |
| 150 | 400.0 | 200.0 | 300.0 | 100.0 | 133.3 | 66.7 | 50.0 | 25.0 |
| 160 | 375.0 | 187.5 | 281.3 | 93.8 | 125.0 | 62.5 | 46.9 | 23.4 |
| 170 | 352.9 | 176.5 | 264.7 | 88.2 | 117.6 | 58.8 | 44.1 | 22.1 |
| 175 | 342.9 | 171.4 | 257.1 | 85.7 | 114.3 | 57.1 | 42.9 | 21.4 |
| 180 | 333.3 | 166.7 | 250.0 | 83.3 | 111.1 | 55.6 | 41.7 | 20.8 |
Qualunque altro valore: `livemind.mastering.ozone_chains.delay_ms(bpm, "1/8d")`.
