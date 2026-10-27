"""Catena di mastering Ozone 11 per tekno (es. 170 BPM, target club -8 LUFS / -1 dBTP).
oz_master.py sweep            -> calibra Gain sul drop (40 s)
oz_master.py full <gain> <wav> -> processa tutto, misura, salva WAV + stato"""
import os
import sys, json, numpy as np, soundfile as sf, pedalboard
from scipy.signal import welch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _paths import OZONE_VST3, master_src  # noqa: E402
import ozbuild, ozrun

CHAIN = ["Equalizer", "Stereo Imager", "Maximizer"]
def params(gain):
    return {
        "Equalizer": {
            # HP pulito sotto il kick
            "Band 1 Enable": 1, "Band 1 Visible": 1, "Band 1 Shape": 6, "Band 1 Frequency": 24, "Band 1 Q": 0.7,
            # kick 63 Hz domina (+17 dB su 200-2k): -1 dB lascia lavorare meglio il limiter
            "Band 2 Enable": 1, "Band 2 Visible": 1, "Band 2 Shape": 0, "Band 2 Frequency": 63, "Band 2 Gain": -1.0, "Band 2 Q": 1.2,
            # risonanza 200 Hz (+6 dB sui vicini)
            "Band 3 Enable": 1, "Band 3 Visible": 1, "Band 3 Shape": 0, "Band 3 Frequency": 200, "Band 3 Gain": -2.0, "Band 3 Q": 2.0,
            # presenza
            "Band 6 Enable": 1, "Band 6 Visible": 1, "Band 6 Shape": 0, "Band 6 Frequency": 3200, "Band 6 Gain": 0.7, "Band 6 Q": 0.9,
            # aria: il mix cala -5/-10 dB sopra 8k
            "Band 7 Enable": 1, "Band 7 Visible": 1, "Band 7 Shape": 2, "Band 7 Frequency": 9000, "Band 7 Gain": 2.0, "Band 7 Q": 0.7,
        },
        "Stereo Imager": {
            "Num Bands": 4, "Band 1 Active": 1, "Band 2 Active": 1, "Band 3 Active": 1,
            "Crossover Cutoff 1": 150, "Crossover Cutoff 2": 2500, "Crossover Cutoff 3": 9000,
            "Band 1 Width Percent": 0, "Band 2 Width Percent": 0, "Band 3 Width Percent": 12, "Band 4 Width Percent": 20,
        },
        "Maximizer": {
            "Mode": 3, "Spectral Shaping Style": 2, "Character": 2.0, "Gain": gain, "Margin": -1.0,
            "Prevent Intersample Clipping": 1,
            "EnableSoftClipping": 1, "SoftClipMix": 40, "SoftClipMode": 1,
            "Enable Transient Shaping": 1, "Transient Shaping": 30,
            "Stereo Link Amounts Linked": 0, "Stereo Link": 40, "Stereo Transient Link Amount": 40,
        },
    }

def params_loud(gain):
    """Profilo club loud (-3/-3.5 LUFS): meno kick/HP piu' alto per liberare headroom,
    meno shelf perche' il clip aggiunge gia' armoniche alte, soft clip piu' presente."""
    pr = params(gain)
    pr["Equalizer"].update({"Band 1 Frequency": 30, "Band 2 Gain": -2.5, "Band 7 Gain": 0.8})
    pr["Maximizer"].update({"SoftClipMix": 60, "Transient Shaping": 20, "Margin": 0.0})  # ceiling 0 dBTP (ISP attivo)
    return pr

PROFILES = {"club": params, "loud": params_loud}

def hf_side(y, sr):
    f, Pm = welch(y.mean(1), sr, nperseg=8192); _, Ps = welch((y[:, 0] - y[:, 1]) / 2, sr, nperseg=8192)
    k = f > 2500; return round(10 * np.log10(Ps[k].sum() / Pm[k].sum()), 1)

if __name__ == "__main__":
    p = pedalboard.load_plugin(str(OZONE_VST3))
    x, sr = sf.read(ozrun.src(), dtype="float32", always_2d=True)
    if sys.argv[1] == "sweep":
        d = x[int(150 * sr):int(190 * sr)]
        print("IN S/M>2.5k", hf_side(d, sr))
        for g in [7, 8.5, 10]:
            p.raw_state = ozbuild.build(CHAIN, params(g))[0]
            y = p.process(d.T.copy(), sr, buffer_size=1024, reset=True).T[sr:]
            ozrun.measure(y, sr, f"g{g}"); print("   S/M>2.5k", hf_side(y, sr))
    else:
        g = float(sys.argv[2]); prof = PROFILES[sys.argv[4] if len(sys.argv) > 4 else "club"]; st, comp = ozbuild.build(CHAIN, prof(g)); p.raw_state = st
        open(sys.argv[3] + ".ozstate", "wb").write(st); open(sys.argv[3] + ".vst3comp", "wb").write(comp)
        lat = p.reported_latency_samples if hasattr(p, "reported_latency_samples") else 0
        y = p.process(x.T.copy(), sr, buffer_size=1024, reset=True).T
        r = ozrun.measure(y, sr, f"FULL g{g}"); print("   S/M>2.5k", hf_side(y, sr))
        sf.write(sys.argv[3], y, sr, subtype="PCM_24")
        json.dump({"gain": g, "I": float(r["I"]), "tp": float(r["tp"])}, open(sys.argv[3] + ".json", "w"))
