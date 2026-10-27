"""Baby Audio Smooth Operator Pro .baby = binario con record
'PARAM..id..<nome>..value..<double LE 8 byte>'. 224 param in unita' reali."""
from __future__ import annotations
import struct


def _index(data: bytes) -> dict:
    """mappa nome_param -> offset del double (8 byte LE)."""
    res, pos = {}, 0
    while True:
        i = data.find(b"PARAM\x00", pos)
        if i < 0:
            break
        j = data.find(b"id\x00", i)
        k = data.find(b"value\x00", i)
        if j < 0 or k < 0:
            break
        name = "".join(chr(b) for b in data[j + 3:k] if 32 <= b < 127)
        res.setdefault(name, k + 9)  # 'value\0'(6) + marker(3) -> double
        pos = k + 6
    return res


def params(data: bytes) -> dict:
    idx = _index(data)
    return {n: struct.unpack_from("<d", data, off)[0] for n, off in idx.items()}


def get_param(data: bytes, name: str, default=None):
    off = _index(data).get(name)
    return struct.unpack_from("<d", data, off)[0] if off is not None else default


def set_param(data: bytes, name: str, value: float) -> bytes:
    b = bytearray(data)
    off = _index(bytes(b)).get(name)
    if off is None:
        raise KeyError(name)
    struct.pack_into("<d", b, off, float(value))
    return bytes(b)
