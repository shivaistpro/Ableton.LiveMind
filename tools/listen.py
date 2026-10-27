"""Capture Live's real output in stereo (WASAPI loopback) and save it as WAV.

livemind.audio.loopback collapses to mono, which throws away the stereo
correlation — the one number that says whether the low end survives a club PA.
This keeps both channels so the usual stem_report measurements apply.

Written as 32-bit float with NO clipping: the old 16-bit writer clipped at
±1.0, so a master that overshoots 0 dBFS (or its inter-sample peaks) read as a
clean 0 dBFS and the true-peak measure was meaningless.

Usage:
  python listen.py <seconds> <name>                      # just capture
  python listen.py <seconds> <name> --play <beat>        # start Live from <beat>,
                                                         # capture, stop, restore loop
Progress/result go to out/listen_status.json, so a caller can follow a long
capture by reading one file instead of polling the bridge (which starved Live).
"""
from __future__ import annotations

import os, sys  # noqa: E401
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _paths import OUT, SHOTS, out_path  # noqa: E402,F401
import json
import os
import struct
import sys
import time

import numpy as np
import soundcard as sc

OUT = str(OUT)
STATUS = os.path.join(OUT, "listen_status.json")


def write_wav_f32(path, x, sr):
    x = np.ascontiguousarray(x, dtype="<f4")
    pcm = x.tobytes()
    ch = x.shape[1]
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVE")
        f.write(b"fmt " + struct.pack("<IHHIIHH", 16, 3, ch, sr,
                                      sr * ch * 4, ch * 4, 32))
        f.write(b"data" + struct.pack("<I", len(pcm)) + pcm)


def status(**kw):
    kw["t"] = time.time()
    try:
        with open(STATUS, "w") as f:
            json.dump(kw, f)
    except OSError:
        pass


def main(seconds, name, play_beat=None, sr=48000):
    lom = None
    loop_state = None
    if play_beat is not None:
        sys.path.insert(0, os.path.dirname(__file__))
        from lom_direct import Lom
        lom = Lom()
        if not lom.ping().get("ok"):
            status(state="error", error="Remote Script irraggiungibile")
            raise SystemExit("Remote Script irraggiungibile")
        lom.call([], "stop_playing")
        loop_state = lom.get([], "loop")
        lom.set([], "loop", False)
        lom.set([], "current_song_time", float(play_beat))

    spk = sc.default_speaker()
    mic = sc.get_microphone(id=str(spk.name), include_loopback=True)
    total = int(seconds * sr)
    chunk = sr  # 1 s
    parts, got = [], 0
    status(state="recording", seconds=seconds, done=0.0, name=name)
    try:
        with mic.recorder(samplerate=sr, channels=2) as rec:
            rec.record(numframes=256)            # warm-up: open the stream first
            if lom is not None:
                lom.call([], "start_playing")
            while got < total:
                n = min(chunk, total - got)
                parts.append(rec.record(numframes=n))
                got += n
                if (got // sr) % 5 == 0:
                    status(state="recording", seconds=seconds, done=got / sr, name=name)
    finally:
        if lom is not None:
            lom.call([], "stop_playing")
            if loop_state is not None:
                lom.set([], "loop", bool(loop_state))

    data = np.concatenate(parts, axis=0)[:total]
    p = os.path.join(OUT, name + ".wav")
    write_wav_f32(p, data, sr)
    peak = float(np.max(np.abs(data))) if data.size else 0.0
    pk = 20 * np.log10(peak) if peak > 0 else -120.0
    status(state="done", path=p, seconds=seconds, sample_peak_db=round(pk, 2), name=name)
    print("catturato %.1fs -> %s  (sample peak %.2f dBFS, float32)" % (seconds, p, pk))


if __name__ == "__main__":
    a = sys.argv[1:]
    beat = None
    if "--play" in a:
        i = a.index("--play")
        beat = float(a[i + 1])
        del a[i:i + 2]
    main(float(a[0]), a[1], beat)
