"""Scrive la catena di oz_master come preset globale utente di Ozone 11 (XML, stesso formato dei preset di fabbrica)."""
import sys, base64, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _paths import OZONE_VST3, master_src  # noqa: E402
import oz_master, ozbuild
TAG = {"Equalizer": "EQ", "Stereo Imager": "Imager", "Maximizer": "Maximizer", "Dynamics": "Dynamics", "Low End Focus": "LowEndFocus"}
def write(path, gain, profile="club"):
    pr = oz_master.PROFILES[profile](gain); ch = base64.b64encode(ozbuild.chain_bytes(oz_master.CHAIN)).decode()
    L = ['<?xml version="1.0" standalone="yes" ?>',
         f'<OzoneMS PresetVer="4" PluginVer="110000" PluginBuild="2942" LastModified="{int(time.time())}">']
    for el in oz_master.CHAIN:
        L.append(f'    <{TAG[el]} Enabled="1">')
        for k, v in pr[el].items():
            L.append(f'        <Param ElementID="{el}" ParamID="{k}" Value="{float(v):.8f}" />')
        L.append(f'        <ExtraBytes ElementID="{el}" Data="" />'); L.append(f'    </{TAG[el]}>')
    L += ['    <Global Enabled="1">', f'        <ExtraBytes ElementID="ElementChain" Data="{ch}" />',
          '        <ExtraBytes ElementID="Global" Data="" />', '    </Global>', '    <Meters Enabled="1" />', '</OzoneMS>']
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")
if __name__ == "__main__":
    write(sys.argv[2], float(sys.argv[1]), sys.argv[3] if len(sys.argv) > 3 else "club"); print("ok", sys.argv[2])
