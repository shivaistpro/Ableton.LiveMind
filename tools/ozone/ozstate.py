"""Codec dello stato VST3 di Ozone 11 (JUCE): 'VC2!' + u32 len + XML <VST3PluginState><IComponent>JUCE-b64</IComponent>.
JUCE MemoryBlock base64: '<nbytes>.' + caratteri 6 bit (alfabeto .ABC..Zabc..z0..9+), little-endian sui bit."""
import struct, re
ALPHA = ".ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+"
IDX = {c: i for i, c in enumerate(ALPHA)}

def juce_b64_decode(s):
    n, body = s.split(".", 1)
    n = int(n); out = bytearray(n); bit = 0
    for ch in body:
        v = IDX[ch]
        for b in range(6):
            if bit >= n * 8: break
            if v >> b & 1: out[bit >> 3] |= 1 << (bit & 7)
            bit += 1
    return bytes(out)

def juce_b64_encode(data):
    n = len(data); total_bits = n * 8; chars = []
    for i in range(0, total_bits, 6):
        v = 0
        for b in range(6):
            bit = i + b
            if bit < total_bits and data[bit >> 3] >> (bit & 7) & 1: v |= 1 << b
        chars.append(ALPHA[v])
    return f"{n}." + "".join(chars)

def unpack(state):
    assert state[:4] == b"VC2!"
    ln = struct.unpack("<I", state[4:8])[0]
    xml = state[8:8 + ln].decode("utf-8").rstrip("\0")
    m = re.search(r"<IComponent>(.*?)</IComponent>", xml, re.S)
    return xml, juce_b64_decode(m.group(1).strip())

def pack(xml_outer, comp):
    x = re.sub(r"<IComponent>.*?</IComponent>", "<IComponent>" + juce_b64_encode(comp) + "</IComponent>", xml_outer, flags=re.S)
    b = x.encode("utf-8") + b"\0"
    return b"VC2!" + struct.pack("<I", len(b)) + b

if __name__ == "__main__":
    import sys
    st = open(sys.argv[1], "rb").read()
    xml, comp = unpack(st)
    assert pack(xml, comp)[8:] .startswith(b"<?xml"); assert juce_b64_decode(juce_b64_encode(comp)) == comp
    print("outer:", re.sub(r"<IComponent>.*?</IComponent>", "<IComponent>...</IComponent>", xml, flags=re.S)[:600])
    print("comp len", len(comp)); print(comp[:1500])
    open(sys.argv[1] + ".comp", "wb").write(comp)
