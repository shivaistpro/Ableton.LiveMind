"""Write FabFilter Pro-Q 3 presets (.ffp) from plain band descriptions.

Format (reverse-engineered from the factory presets):

    b"FQ3p" | uint32 version(4) | uint32 count(334) | 334 float32

    float[0]        number of bands in use
    float[1 + i*13] band i, 13 fields, 24 slots
    float[314:]     21 trailing globals (output gain, analyser, etc.)

Band fields
    0  enabled            1 / 0
    1  frequency          log2(Hz)
    2  gain               dB
    3  dynamic range      dB (0 = static band)
    4  unknown, always 1
    5  unknown, always 1
    6  Q                  normalised: log10(Q) = v*3.20412 - 1.60206
    7  shape              see SHAPES
    8  slope              index into SLOPES
    9  stereo placement   0 L, 1 R, 2 Stereo, 3 Mid, 4 Side
    10 slot in use        1
    11 unknown, 0
    12 dynamic mode flag  0 / 1

The 21 trailing globals are copied verbatim from a factory template, so
anything not modelled here keeps its default instead of being zeroed.
"""
from __future__ import annotations
import os
import struct

N_FLOATS = 334
N_BANDS = 24
BAND_LEN = 13

SHAPES = {"bell": 0, "lowshelf": 1, "lowcut": 2, "highshelf": 3,
          "highcut": 4, "notch": 5, "bandpass": 6, "tiltshelf": 7,
          "flattilt": 8}
SLOPES = [6, 12, 18, 24, 30, 36, 48, 72, 96]   # dB/oct; index 9 = brickwall
STEREO = {"stereo": 2, "left": 0, "right": 1, "mid": 3, "side": 4}

import math


def q_to_norm(q: float) -> float:
    return (math.log10(max(q, 0.025)) + 1.60206) / 3.20412


def norm_to_q(v: float) -> float:
    return 10 ** (v * 3.20412 - 1.60206)


def slope_index(db_per_oct) -> int:
    if isinstance(db_per_oct, str) and db_per_oct.lower().startswith("brick"):
        return 9
    return min(range(len(SLOPES)), key=lambda i: abs(SLOPES[i] - db_per_oct))


def band(freq, shape="bell", gain=0.0, q=1.0, slope=24, stereo="stereo",
         dyn_range=0.0, enabled=True):
    """One EQ band. freq in Hz, gain and dyn_range in dB, slope in dB/oct."""
    f = [0.0] * BAND_LEN
    f[0] = 1.0 if enabled else 0.0
    f[1] = math.log2(max(freq, 1.0))
    f[2] = float(gain)
    f[3] = float(dyn_range)
    f[4] = 1.0
    f[5] = 1.0
    f[6] = q_to_norm(q)
    f[7] = float(SHAPES[shape.lower()])
    f[8] = float(slope_index(slope))
    f[9] = float(STEREO[stereo.lower()])
    f[10] = 1.0
    f[11] = 0.0
    f[12] = 1.0 if dyn_range else 0.0
    return f


def read_ffp(path):
    raw = open(path, "rb").read()
    if raw[:4] != b"FQ3p":
        raise ValueError("non e' un preset Pro-Q 3: %s" % path)
    ver, n = struct.unpack_from("<II", raw, 4)
    return ver, list(struct.unpack_from("<%df" % n, raw, 12))


def write_ffp(path, bands, template=None):
    """Write bands to a .ffp, keeping the template's global tail."""
    if template and os.path.exists(template):
        ver, data = read_ffp(template)
    else:
        ver, data = 4, [0.0] * N_FLOATS
        for i in range(N_BANDS):                     # sane empty slots
            base = 1 + i * BAND_LEN
            data[base + 1] = math.log2(1000.0)
            data[base + 4] = data[base + 5] = 1.0
            data[base + 6] = q_to_norm(1.0)
            data[base + 9] = 2.0
            data[base + 10] = 1.0
    if len(bands) > N_BANDS:
        raise ValueError("massimo %d bande" % N_BANDS)

    data[0] = float(len(bands))
    for i in range(N_BANDS):
        base = 1 + i * BAND_LEN
        if i < len(bands):
            data[base:base + BAND_LEN] = bands[i]
        else:
            data[base] = 0.0                          # slot spento

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"FQ3p")
        f.write(struct.pack("<II", ver, len(data)))
        f.write(struct.pack("<%df" % len(data), *data))
    return path


def describe(path):
    ver, f = read_ffp(path)
    n = int(round(f[0]))
    out = []
    inv_shape = {v: k for k, v in SHAPES.items()}
    for i in range(n):
        s = f[1 + i * BAND_LEN: 1 + (i + 1) * BAND_LEN]
        sl = SLOPES[int(s[8])] if int(s[8]) < len(SLOPES) else "brickwall"
        out.append("%-9s %8.1f Hz  %+5.1f dB  Q=%.2f  %s dB/oct  dyn=%.0f"
                   % (inv_shape.get(int(s[7]), "?"), 2 ** s[1], s[2],
                      norm_to_q(s[6]), sl, s[3]))
    return out


def _self_check():
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "_proq3_check.ffp")
    bands = [
        band(31, "lowcut", slope=24, q=0.7),
        band(91, "bell", gain=-3.5, q=2.4),
        band(6200, "highshelf", gain=2.0, q=0.7),
    ]
    write_ffp(tmp, bands)
    ver, f = read_ffp(tmp)
    assert int(round(f[0])) == 3, f[0]
    assert abs(2 ** f[1 + 1] - 31) < 0.1, 2 ** f[2]
    assert int(f[1 + 7]) == SHAPES["lowcut"]
    assert abs(norm_to_q(f[1 + BAND_LEN + 6]) - 2.4) < 0.01
    assert abs(f[1 + BAND_LEN + 2] + 3.5) < 0.001
    assert f[1 + 3 * BAND_LEN] == 0.0, "quarta banda deve essere spenta"
    os.remove(tmp)
    print("proq3 self-check ok")


if __name__ == "__main__":
    _self_check()
