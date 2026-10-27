# Reference per `livemind.audio.reference`

Una cartella per genere (`hardtek/`, `tekno_tribe/`, `acid/`, `hardflor/`), dentro
i master di riferimento in WAV (o FLAC/AIFF se c'e' `soundfile`). L'audio non va su
Git; la cache delle misure (`.metrics_cache.json`) si rigenera da sola.

    python -m livemind.audio.reference mix.wav --genre hardtek

La repo non contiene audio: ogni utente mette qui i propri reference (3+ brani
per genere, master finiti, drop rappresentativi). Per aggiungere un genere basta
creare la cartella e copiarci i brani.
