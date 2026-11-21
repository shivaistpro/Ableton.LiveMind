"""Risonanze ed errori di UN brano, senza confrontarlo con altri (metodo del 21/11).

Un picco si taglia solo se NON e' musica:
- armonica della fondamentale del kick/basso (f0 stimata dal picco piu' forte 35-90 Hz) -> non si tocca;
- nota della scala del brano (+-30 cent da una delle classi di altezza forti) -> non si tocca;
- fuori scala ma presente <30% del tempo -> evento (fx, colpo): banda dinamica solo se fischia;
- fuori scala e presente quasi sempre -> risonanza fissa: taglio stretto e piccolo.
Controlla anche rumble sotto 30 Hz, DC e sub non mono.

Uso: python res_detect.py <file.wav> [inizio_s] [fine_s]
"""
import sys

import numpy as np
import soundfile as sf

NOTE = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
N, HOP = 32768, 16384


def analyse(path, t0=0.0, t1=None):
    info = sf.info(path)
    sr = info.samplerate
    x, _ = sf.read(path, dtype='float32', start=int(t0 * sr), stop=None if t1 is None else int(t1 * sr))
    mid, side = (x[:, 0] + x[:, 1]) / 2, (x[:, 0] - x[:, 1]) / 2
    w = np.hanning(N).astype(np.float32)
    nf = (len(mid) - N) // HOP
    P = np.empty((nf, N // 2 + 1), np.float32)
    PS = np.zeros(N // 2 + 1)
    for i in range(nf):
        s = slice(i * HOP, i * HOP + N)
        P[i] = np.abs(np.fft.rfft(mid[s] * w)) ** 2
        PS += np.abs(np.fft.rfft(side[s] * w)) ** 2
    f = np.fft.rfftfreq(N, 1 / sr)
    Pm = P.mean(0)
    L = 10 * np.log10(Pm + 1e-20)
    rep = {}
    lo = (f > 35) & (f < 90)
    f0 = f[lo][np.argmax(Pm[lo])]
    rep['f0'] = f0
    ch = np.zeros(12)
    for i in np.where((f > 40) & (f < 2000))[0]:
        ch[int(round(69 + 12 * np.log2(f[i] / 440))) % 12] += Pm[i]
    ch = 10 * np.log10(ch / ch.max())
    strong = {k for k in range(12) if ch[k] > -9}
    rep['scala'] = [NOTE[k] for k in np.argsort(-ch) if k in strong]
    band = lambda a, b: Pm[(f >= a) & (f < b)].sum()
    rep['rumble_dB'] = 10 * np.log10(band(5, 30) / band(30, 120))
    rep['sub_side_dB'] = 10 * np.log10(PS[(f > 30) & (f < 120)].sum() / nf / band(30, 120))
    rep['dc_dB'] = float(20 * np.log10(np.abs(x.mean(0)).max() + 1e-12))
    peaks = []
    lf = np.log2(np.maximum(f, 1))
    for i in np.where((f > 30) & (f < 16000))[0]:
        if L[i] < L[max(0, i - 6):i + 7].max():
            continue
        env = 10 * np.log10(np.median(Pm[np.abs(lf - lf[i]) < 1 / 6]))
        if L[i] - env < 6:
            continue
        m = 69 + 12 * np.log2(f[i] / 440)
        h = f[i] / f0
        fr = 10 * np.log10(P[:, i] + 1e-20) - 10 * np.log10(np.median(P[:, i - 60:i + 61], axis=1) + 1e-20)
        # le armoniche di un kick distorto con glide stanno entro ~2% dal multiplo esatto
        harm = round(h) <= 12 and abs(h - round(h)) < 0.02 * round(h)
        in_key = int(round(m)) % 12 in strong and abs(m - round(m)) < 0.3
        pres = (fr > 10).mean()
        if harm:
            kind = 'armonica %d del kick' % round(h)
        elif in_key:
            kind = 'nota %s' % NOTE[int(round(m)) % 12]
        elif pres < 0.3:
            kind = 'evento (suono che passa): dinamica solo se fischia'
        else:
            kind = 'RISONANZA FISSA: taglio stretto'
        peaks.append(dict(f=float(f[i]), prom=float(L[i] - env), max_prom=float(fr.max()),
                          presenza=float(pres), cent=float((m - round(m)) * 100), tipo=kind))
    rep['picchi'] = peaks
    return rep


def main():
    a = sys.argv[1:]
    r = analyse(a[0], float(a[1]) if len(a) > 1 else 0.0, float(a[2]) if len(a) > 2 else None)
    print("fondamentale kick/basso %.1f Hz | scala: %s" % (r['f0'], ' '.join(r['scala'])))
    print("rumble 5-30 Hz vs 30-120: %.1f dB | sub side/mid: %.1f dB | DC: %.1f dBFS"
          % (r['rumble_dB'], r['sub_side_dB'], r['dc_dB']))
    for p in r['picchi']:
        print("%8.1f Hz  prom %+5.1f (max %+5.1f)  presente %3.0f%%  %+4.0fc  %s"
              % (p['f'], p['prom'], p['max_prom'], p['presenza'] * 100, p['cent'], p['tipo']))


if __name__ == '__main__':
    main()
