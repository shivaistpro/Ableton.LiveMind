# Knowledge base di LIVEMIND

Conoscenza tecnica consultabile da LIVEMIND (tool `knowledge`) e da qualunque
sessione Claude che lavori nel repo. Un file per argomento, sezioni `##`/`###`
brevi e cercabili.

| Topic | Contenuto |
|---|---|
| `mastering/ozone11` | iZotope Ozone 11: ogni modulo, parametri e range dal manuale ufficiale, flusso di lavoro, catene per genere |
| `mastering/mastering-techniques` | Mastering completo: loudness per destinazione (dati 2026), ordine della catena, EQ, dinamica, stereo, clipping/limiting, dither, QC |
| `mastering/compression` | Tutti i compressori (VCA/FET/Opto/Vari-mu/diode/PWM/digitale), upward/downward, parallel, sidechain, settaggi per sorgente |
| `mastering/span-plus` | Voxengo SPAN Plus: modi di analisi (RT Avg/Max/Sigma), block/window/overlap, meter LUFS/K/true peak, correlazione, spettri statici e CSV, import/export multitraccia, setup consigliati |
| `mastering/return-fx` | Return track: riverberi, delay, parallel, rumble kick, trucchi tekno/tribe/acid, tabella ms per BPM |

Uso dal bridge:

    {"id":"kb1","tool":"knowledge","args":{"action":"search","query":"IRC 4 transient"}}
    {"id":"kb2","tool":"knowledge","args":{"action":"ozone_chain","genre":"hardtek","destination":"club"}}
    {"id":"kb3","tool":"knowledge","args":{"action":"delay_ms","bpm":175,"division":"1/8d"}}
    {"id":"kb4","tool":"knowledge","args":{"action":"read","topic":"mastering/return-fx"}}

Da Python: `from livemind.brain import kb; kb.search("sidechain reverb")`.

Regola: i numeri marcati come ipotesi vanno validati con le misure
(`livemind.audio.loopback`, `livemind.audio.reference`) prima di fidarsi.
