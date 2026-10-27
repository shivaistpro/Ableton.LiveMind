"""Rende importabile livemind.paths dagli script in tools/ (lanciati come file)."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from livemind.paths import OUT, SHOTS, ROOT, OZONE_VST3, KICK3_PRESETS, master_src, out_path  # noqa: E402,F401
