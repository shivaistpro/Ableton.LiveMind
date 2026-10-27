"""Serum 2 .SerumPreset = 'XferJson' + 0x00 + uint32(lenJSON) + 4x00 + JSON
+ uint32(sizeCBOR) + uint32(flag) + zstd(CBOR). Scrittura validata (hash non verificato)."""
from __future__ import annotations
import struct, json
try:
    import zstandard as zstd
    import cbor2
    _OK = True
except Exception:  # pragma: no cover
    _OK = False

MAGIC = b"XferJson"


def loads(raw: bytes):
    """Ritorna (hdr:dict, flag:int, obj:dict)."""
    if not _OK:
        raise RuntimeError("pip install zstandard cbor2 --break-system-packages")
    if raw[:8] != MAGIC:
        raise ValueError("non e' un .SerumPreset (magic XferJson mancante)")
    jlen = struct.unpack_from("<I", raw, 9)[0]
    hdr = json.loads(raw[17:17 + jlen])
    p = 17 + jlen
    usize, flag = struct.unpack_from("<II", raw, p)
    p += 8
    obj = cbor2.loads(zstd.ZstdDecompressor().decompress(raw[p:], max_output_size=usize + 1 << 16))
    return hdr, flag, obj


def dumps(hdr: dict, flag: int, obj: dict) -> bytes:
    if not _OK:
        raise RuntimeError("pip install zstandard cbor2 --break-system-packages")
    cbor = cbor2.dumps(obj)
    comp = zstd.ZstdCompressor(level=19).compress(cbor)
    jb = json.dumps(hdr, separators=(",", ":")).encode()
    return (MAGIC + b"\x00" + struct.pack("<I", len(jb)) + b"\x00\x00\x00\x00"
            + jb + struct.pack("<II", len(cbor), flag) + comp)


def load(path: str):
    return loads(open(path, "rb").read())


def save(path: str, hdr, flag, obj):
    open(path, "wb").write(dumps(hdr, flag, obj))


def pp(obj: dict, module: str) -> dict:
    """plainParams di un modulo, creandolo se assente."""
    obj.setdefault(module, {})
    if not isinstance(obj[module].get("plainParams"), dict):
        obj[module]["plainParams"] = {}
    return obj[module]["plainParams"]


def set_param(obj: dict, module: str, key: str, value: float):
    pp(obj, module)[key] = value


def get_param(obj: dict, module: str, key: str, default=None):
    m = obj.get(module, {})
    return m.get("plainParams", {}).get(key, default) if isinstance(m, dict) else default


# helper di alto livello (mappa architettura Serum 2)
SUB = "Oscillator4"       # oscillatore SUB (sinusoide pura)
OSC_A, OSC_B, OSC_C = "Oscillator0", "Oscillator1", "Oscillator2"
NOISE = "Oscillator3"


def enable_osc(obj, module, on=True, volume=None):
    set_param(obj, module, "kParamEnable", 1.0 if on else 0.0)
    if volume is not None:
        set_param(obj, module, "kParamVolume", float(volume))


def mono(obj, on=True):
    set_param(obj, "Global0", "kParamMonoToggle", 1.0 if on else 0.0)


def master(obj, value):
    set_param(obj, "Global0", "kParamMasterVolume", float(value))
