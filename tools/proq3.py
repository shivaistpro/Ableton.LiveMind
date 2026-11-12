"""Write FabFilter Pro-Q 3 presets (.ffp) from plain band descriptions.

Format (reverse-engineered from the factory presets):

    b"FQ3p" | uint32 version(4) | uint32 count(334) | 334 float32

    float[i*13 : i*13+13]   band i, 13 fields, 24 slots (floats 0..311)
    float[312:]             22 trailing globals (output gain, analyser, etc.)

Band fields
    0  used               1 / 0  (0 = slot empty, band not shown)
    1  enabled            1 / 0  (0 = band shown but bypassed)
    2  frequency          log2(Hz)
    3  gain               dB
    4  dynamic range      dB (0 = static band)
    5  unknown, always 1
    6  unknown, always 1
    7  Q                  normalised: log10(Q) = v*3.20412 - 1.60206
    8  shape              see SHAPES
    9  slope              index into SLOPES
    10 stereo placement   0 L, 1 R, 2 Stereo, 3 Mid, 4 Side
    11 unknown, always 1
    12 unknown, 0

Earlier versions assumed float[0] was a band count and shifted every band by
one float: each band's "used" flag then came from the previous band's last
field, so bands vanished (a static band hid the next one) or empty slots
showed up at 1 kHz. Checked against Pro-Q 3: the factory "Default Setting"
has all slots enabled but every "used" flag at 0, and shows no bands.

The 22 trailing globals are copied verbatim from a factory template, so
anything not modelled here keeps its default instead of being zeroed.
"""
from __future__ import annotations
import math
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
    return [1.0,
            1.0 if enabled else 0.0,
            math.log2(max(freq, 1.0)),
            float(gain),
            float(dyn_range),
            1.0, 1.0,
            q_to_norm(q),
            float(SHAPES[shape.lower()]),
            float(slope_index(slope)),
            float(STEREO[stereo.lower()]),
            1.0, 0.0]


def _empty_band():
    b = band(1000.0)
    b[0] = 0.0                                       # slot not used
    return b


def read_ffp(path):
    raw = open(path, "rb").read()
    if raw[:4] != b"FQ3p":
        raise ValueError("non e' un preset Pro-Q 3: %s" % path)
    ver, n = struct.unpack_from("<II", raw, 4)
    return ver, list(struct.unpack_from("<%df" % n, raw, 12))


def write_ffp(path, bands, template=None):
    """Write bands to a .ffp, keeping the template's global tail."""
    if len(bands) > N_BANDS:
        raise ValueError("massimo %d bande" % N_BANDS)
    if template and os.path.exists(template):
        ver, data = read_ffp(template)
    else:
        ver, data = 4, [0.0] * N_FLOATS
    for i in range(N_BANDS):
        base = i * BAND_LEN
        data[base:base + BAND_LEN] = bands[i] if i < len(bands) else _empty_band()

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"FQ3p")
        f.write(struct.pack("<II", ver, len(data)))
        f.write(struct.pack("<%df" % len(data), *data))
    return path


def used_bands(floats):
    """Band records (13 floats each) whose 'used' flag is set."""
    return [floats[i * BAND_LEN:(i + 1) * BAND_LEN] for i in range(N_BANDS)
            if floats[i * BAND_LEN] >= 0.5]


def describe(path):
    _, f = read_ffp(path)
    inv_shape = {v: k for k, v in SHAPES.items()}
    out = []
    for s in used_bands(f):
        sl = SLOPES[int(s[9])] if int(s[9]) < len(SLOPES) else "brickwall"
        out.append("%-9s %8.1f Hz  %+5.1f dB  Q=%.2f  %s dB/oct  dyn=%+.1f%s"
                   % (inv_shape.get(int(s[8]), "?"), 2 ** s[2], s[3],
                      norm_to_q(s[7]), sl, s[4],
                      "" if s[1] >= 0.5 else "  (off)"))
    return out


def _self_check():
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "_proq3_check.ffp")
    # a static band followed by a dynamic one: the old layout hid the second
    bands = [
        band(31, "lowcut", slope=24, q=0.7),
        band(190, "bell", gain=-1.0, q=1.0),
        band(228, "bell", q=6, dyn_range=-1.5),
        band(6200, "highshelf", gain=2.0, q=0.7),
    ]
    write_ffp(tmp, bands)
    _, f = read_ffp(tmp)
    used = used_bands(f)
    assert len(used) == 4, len(used)
    assert abs(2 ** used[0][2] - 31) < 0.1
    assert int(used[0][8]) == SHAPES["lowcut"]
    assert abs(2 ** used[2][2] - 228) < 0.1 and used[2][4] == -1.5
    assert abs(norm_to_q(used[2][7]) - 6) < 0.01
    assert f[4 * BAND_LEN] == 0.0, "quinto slot deve essere vuoto"
    os.remove(tmp)
    print("proq3 self-check ok")


if __name__ == "__main__":
    _self_check()
