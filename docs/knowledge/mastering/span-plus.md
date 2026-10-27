# Voxengo SPAN Plus — riferimento completo per LIVEMIND

Fonti: SPAN Plus User Guide v1.25 e Voxengo Primary User Guide (letti per intero
nelle parti rilevanti). Cio' che e' marcato **[uso]** e' prassi nostra.

SPAN Plus = analizzatore FFT in tempo reale + meter (RMS/K-system/EBU R128 LUFS,
true peak, crest factor, correlazione). Versione estesa del SPAN gratuito:
in piu' ha **import/export multitraccia** degli spettri, **Save PNG**, spettri
statici con **CSV**, modalita' **Wide**. Non tocca l'audio (tranne la modalita'
sweep/solo). Nessun ingresso sidechain: per vedere piu' tracce si usa Import/Export.

---

## 1. Pannello spettro
- Colore del gruppo di canali corrente; lo **spettro secondario** e' piu' scuro.
- **Ctrl + click tenuto** sullo spettro = sweep/solo a banda stretta (ascolti solo
  quella zona). Rilasciato: nessun effetto sull'audio.
- **Hold**: congela l'immagine per confronti visivi.
- **Underlay**: mostra lo spettro di un altro gruppo di canali della stessa istanza
  (es. routing preset **Dual Mono** + Underlay = Right → L e R sovrapposti;
  routing **Mid-Side** → Mid e Side sovrapposti).
- **Click destro**: copia la frequenza puntata negli appunti (da incollare nell'EQ).
- **Save PNG**: salva l'immagine dello spettro.
- **Static**: editor degli spettri statici (vedi sezione 4).
- **Import / Export To**: spettri multitraccia (sezione 5).
- **Mode**: modalita' di analisi (sezione 2).
- **Wide**: nasconde meter e statistiche, spettro a tutta larghezza.
- **Default Slope = 4.5 dB/oct**: lo spettro appare "sollevato" sugli alti rispetto
  ad altri analizzatori. Ozone usa 3 dB/oct (rumore rosa piatto). Per confrontare
  immagini tra i due, mettere la stessa slope.

## 2. Spectrum Mode Editor (i parametri che contano)
- **Type**:
  - **RT Avg**: media in tempo reale su "Avg Time" → bilanciamento tonale.
  - **RT Max**: massimo in tempo reale con decadimento → picchi.
  - **Max**: massimo cumulativo (= peak hold infinito).
  - **Avg**: media cumulativa (per "fotografare" una sezione intera).
  - **RT Sigma**: quanto e' dinamica ogni zona. Usarlo con RT Avg e Avg Time
    < 1000 ms: dove Sigma sta sopra/uguale all'Avg la zona e' molto dinamica
    (e' cio' che attira l'attenzione), sotto = zona statica.
- **2nd Spectrum + 2nd Type**: es. Type RT Avg + 2nd RT Max → media e picchi
  insieme; la distanza tra le due curve ≈ dinamica del materiale in quella banda.
- **Block Size** (FFT): alto = piu' risoluzione sui bassi, meno precisione nel tempo
  sugli alti, refresh piu' lento e piu' latenza visiva. A sample rate alte serve un
  block piu' grande per la stessa risoluzione. Per misurare la frequenza di kick/basso:
  **Block Size alto + Overlap alto**. Se l'audio fa click, alzare il buffer della DAW.
- **Window**: **Hann** (default, musica, buona separazione sui bassi),
  **Hi-Res** (Nuttall al quadrato: analisi tecnica, rumore di fondo, artefatti),
  **Blackman** (via di mezzo), **Dome** (piu' risoluzione in frequenza di Hann ma
  peggio con componenti deboli e block grandi).
- **Overlap** %: refresh piu' frequente, piu' CPU.
- **Avg Time** (ms): tempo per scendere di 20 dB (RT Avg / RT Max).
- **Smooth** (ottave): solo visivo. Con sinusoidi stazionarie crea un calo apparente
  di 6 dB/oct (non succede sulla musica).
- **Offset**: **Normalize** (frequenze piu' forti in cima) / **Center** (centra tutti
  gli spettri: toglie la differenza di volume nei confronti tra tracce).
- Freq Low/High, Range Low/High, **Slope** (dB/oct attorno a 1 kHz), Anti-Alias,
  **Align 0 dB** (sinusoide 1 kHz a 0 dBFS = 0 dB sul grafico; con Slope 0 per misure
  tecniche).

## 3. Meter e statistiche
### Statistics (dall'ultimo reset o dall'avvio del play)
- **RMS / Integr**: potenza integrata (in modalita' LUFS = loudness integrata).
- **Max Crest Factor**: differenza massima tra peak-RMS (finestra 50 ms) e RMS.
  RMS + Max Crest = peak RMS. Confrontabile con altri plug-in solo con la stessa
  finestra di peak-RMS.
- **True Peak / Peak**: switch **TP** per scegliere true peak o sample peak;
  segnala i campioni che clipperebbero. Utile anche col dither con noise shaping
  aggressivo a bassa bit depth (il rumore puo' superare 0 dBFS).
- **Reset**: azzera. **[uso]** Resettare all'inizio del drop per misurare solo quello.

### Metering (selettore)
- **dBFS / dBFS.30 / dBFS.15**: nessun bias, range diversi.
- **dBFS+3**: +3 dB su meter e RMS (picchi invariati); con "Align 0 dB" e Slope 0
  fa combaciare spettro e meter.
- **K-20 / K-14 / K-12** (Bob Katz) e **K-20 C / K-14 C / K-12 C** (calibrazione):
  integrazione e release fissi a 600 ms, nessuna pesatura.
- **LUFS / LU** (EBU R128, ITU-R BS.1770-4, Tech 3341-2016; manca la scala +18 e il
  riepilogo): suffisso **ML** = momentary (0.4 s) sul meter, **SL** = short-term (3 s).
  L'integrato va nel pannello "Integr", aggiornato 2 volte al secondo e calcolato solo
  sugli **ultimi 5 minuti** dal reset.
- Ballistiche del meter (integrazione, release, peak hold) nelle Settings globali
  (valgono per tutte le istanze); nei modi K e LUFS sono fisse.

### Correlation Meter
- Correlazione media tra i primi due canali su **500 ms**; bilanciamento medio in dB
  sugli ultimi **3 s** (negativo = sinistro piu' forte).
- Interpretazione (Voxengo): +1 = in fase/mono, 0 = scorrelati (stereo ampio),
  −1 = controfase. Range accettabile per lo stereo 0…+1; valori negativi non sono
  mono-compatibili. Uno stereo scorrelato suona ~1.25 dB piu' forte di uno correlato
  a pari picco.

## 4. Spettri statici (Static Spectrums Editor)
- Slot con nome, colore, **shift in dB** (solo posizione, non forma), visibilita'.
- **Take / Take 2nd**: fotografa lo spettro primario/secondario con i parametri del
  Mode corrente. Prima: Type **Avg** o **Max** (o preset "Average" / "Avg+Max"),
  analizzare abbastanza a lungo. Una foto per sezione (intro, drop, break):
  click sullo spettro per resettare tra una foto e l'altra.
- **Predef**: curve predefinite ("Combined −4.5/oct" = C-weighting ritoccata
  + −4.5 dB/oct).
- **Load / Save**: `.csf` o **`.csv`** (frequenze lineari in Hz, potenza in dB) —
  e **si puo' caricare direttamente un file audio** `.wav`, `.aiff`, `.flac`.
- **[uso] per LIVEMIND**: caricare i reference di `references/<genere>/` come spettri
  statici (colori diversi, Offset **Center**) e sovrapporli allo spettro del master:
  confronto tonale immediato e indipendente dal volume. Il CSV salvato e' leggibile
  da Python per confronti numerici.

## 5. Import/Export multitraccia
- SPAN Plus su ogni traccia da osservare. Sulle tracce "sorgente": **Export To** uno
  slot libero (nome istanza = nome traccia). Sulla traccia di "visione": **Import**
  → gli **Import From**. Colore e riempimento vengono dall'istanza che esporta;
  risoluzione e tipo dal suo Mode.
- Lasciare Export To su `---` quando non serve (CPU). Mai due istanze sullo stesso
  slot (succede copiando istanze o caricando preset): risultati incerti.
- **[uso] masking kick/basso**: SPAN Plus su kick ed export, SPAN Plus sul basso con
  import del kick → si vede dove il fondamentale del kick (hard techno ~55-65 Hz) e il
  basso si sovrappongono; decidere tagli/sidechain. Stesso trucco per 303 vs lead,
  percussioni tribali vs hat.

## 6. Routing (comune a tutti i Voxengo)
- **Routing Presets** condivisi tra plug-in Voxengo: Stereo, **Dual Mono**,
  **Mid-Side** ecc. Gruppi di canali (G-1, G-2...) con parametri propri; **Solo** del
  gruppo; **Copy** tra gruppi.
- **Show All Channel Meters** (finestra Channel Routing): vedere meter di L/R o M/S
  insieme.
- **[uso] check mono dei bassi**: routing Mid-Side, gruppo Side in primo piano con
  Underlay = Mid: sotto 100-150 Hz la curva Side deve essere molto piu' bassa del Mid
  (idealmente assente).

## 7. Setup consigliati (preset di Mode da salvare)
| Scopo | Type / 2nd | Block | Overlap | Avg Time | Window | Slope | Smooth |
|---|---|---|---|---|---|---|---|
| Bilanciamento tonale del master | RT Avg / RT Max | 8192 | 75% | 3000 ms | Hann | 4.5 (o 3 come Ozone) | 1/3 oct |
| Frequenza esatta di kick/basso | RT Max | 16384-32768 | 90% | 1000 ms | Hann/Dome | 0 | off |
| Dinamica per banda (cosa "salta fuori") | RT Avg / RT Sigma | 4096 | 75% | 500-800 ms | Hann | 4.5 | 1/6 oct |
| Foto di una sezione / reference | Avg (cumulativo) | 8192 | 50% | — | Hann | 4.5 | 1/3 oct |
| Rumore di fondo, aliasing, dither | RT Max | 16384 | 75% | 3000 ms | Hi-Res | 0 | off |
Valori [uso], non di fabbrica.

Meter: **LUFS SL** sul Main track (short-term del drop come in
`mastering-techniques.md`), **TP** attivo, Reset all'inizio della sezione misurata.

## 8. Posizione nella catena e flusso con LIVEMIND
- Sul Main track: **dopo** il limiter (Ozone Maximizer) per misurare cio' che esce.
  Un secondo SPAN Plus **prima** di Ozone serve per vedere cosa cambia il master.
- Sulle tracce: per masking (sezione 5) e per il pitch del kick.
- Per far "vedere" a LIVEMIND l'analizzatore: **Save PNG** (immagine che Claude puo'
  guardare) o **Save CSV** di uno spettro statico (numeri). Le misure ufficiali di
  LIVEMIND restano `livemind.audio.loopback` e `livemind.audio.reference`: SPAN Plus
  e' il controllo visivo in tempo reale, da far combaciare con quelle.
- Limiti noti: integrato LUFS solo sugli ultimi 5 minuti; lo smoothing inganna sulle
  sinusoidi pure; la slope 4.5 dB/oct fa sembrare gli alti piu' forti di quanto
  appaiano in Ozone.
