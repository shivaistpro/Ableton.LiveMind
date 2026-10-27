"""Is the loopback capture a 1:1 copy of Live's master? Check before measuring.

WASAPI loopback on many consumer drivers (Realtek in particular) is taken AFTER
the Windows endpoint volume and the per-app session volume. A system volume at
40% makes a -8 LUFS master read as -16 LUFS and every level decision built on
that capture is wrong. This reads both volumes and reports the gain offset.

Usage: python audio_route_check.py [--fix]   (--fix sets both to 100%)
Needs: pip install pycaw comtypes
"""
from __future__ import annotations

import json
import math
import sys

from pycaw.pycaw import AudioUtilities


def main(fix=False):
    dev = AudioUtilities.GetSpeakers()
    ep = dev.EndpointVolume
    out = {"device": dev.FriendlyName,
           "endpoint_scalar": round(ep.GetMasterVolumeLevelScalar(), 4),
           "endpoint_db": round(ep.GetMasterVolumeLevel(), 2),
           "endpoint_mute": bool(ep.GetMute()), "sessions": []}
    for s in AudioUtilities.GetAllSessions():
        if s.Process and "ableton" in s.Process.name().lower():
            v = s.SimpleAudioVolume
            out["sessions"].append({"process": s.Process.name(),
                                    "scalar": round(v.GetMasterVolume(), 4),
                                    "mute": bool(v.GetMute())})
            if fix:
                v.SetMasterVolume(1.0, None)
                v.SetMute(0, None)
    if fix:
        ep.SetMasterVolumeLevelScalar(1.0, None)
        ep.SetMute(0, None)
        out["fixed"] = True
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main("--fix" in sys.argv)
