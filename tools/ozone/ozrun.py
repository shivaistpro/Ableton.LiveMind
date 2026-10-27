"""ozrun.py <config.json> [out.wav] : processa $LIVEMIND_MASTER_SRC con Ozone 11 (stato costruito) e misura.
config = {"chain":[...], "params":{...}}"""
import os
import sys, json, time, numpy as np, soundfile as sf, pedalboard, pyloudnorm as pyln
from scipy.signal import resample_poly, welch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _paths import OZONE_VST3, master_src  # noqa: E402
import ozbuild


def src():
    """Mix sorgente: variabile d'ambiente LIVEMIND_MASTER_SRC."""
    return str(master_src())


def measure(y, sr, tag):
    m = pyln.Meter(sr); I = m.integrated_loudness(y)
    tp = 20 * np.log10(np.abs(resample_poly(y, 4, 1, axis=0)).max() + 1e-12)
    st = [m.integrated_loudness(y[i:i + 3 * sr]) for i in range(0, len(y) - 3 * sr, sr)]
    st = np.array([v for v in st if np.isfinite(v)]); stmax = st.max()
    mono = y.mean(1); f, P = welch(mono, sr, nperseg=16384)
    def band(lo, hi): k = (f >= lo) & (f < hi); return 10 * np.log10(P[k].sum() + 1e-20)
    ref = band(200, 2000)
    b = {n: round(band(lo, hi) - ref, 1) for n, lo, hi in [("sub20-45", 20, 45), ("kick45-90", 45, 90), ("low90-160", 90, 160), ("box160-300", 160, 300), ("pres2-5k", 2000, 5000), ("hi5-10k", 5000, 10000), ("air10-16k", 10000, 16000)]}
    corr = np.corrcoef(y[:, 0], y[:, 1])[0, 1]
    print(f"[{tag}] I={I:.2f} LUFS  TP={tp:.2f} dBTP  STmax={stmax:.1f}  PLR={tp - I:.1f}  corr={corr:.3f}  bands={b}")
    return dict(I=I, tp=tp, stmax=stmax, bands=b)

if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1]))
    x, sr = sf.read(src(), dtype="float32", always_2d=True)
    seg = cfg.get("seconds")
    if seg: x = x[int(seg[0] * sr):int(seg[1] * sr)]
    t = time.time()
    p = pedalboard.load_plugin(str(OZONE_VST3))
    st, comp = ozbuild.build(cfg["chain"], cfg["params"])
    p.raw_state = st
    open(sys.argv[1].replace(".json", ".state"), "wb").write(st)
    y = p.process(x.T.copy(), sr, buffer_size=1024, reset=True).T
    lat = cfg.get("latency", 0)
    print("proc s", round(time.time() - t, 1), "shape", y.shape)
    measure(x, sr, "IN ")
    r = measure(y, sr, "OUT")
    if len(sys.argv) > 2: sf.write(sys.argv[2], y, sr, subtype="PCM_24")
