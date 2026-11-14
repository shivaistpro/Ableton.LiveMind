"""Aggiunge in coda una traccia audio armata in ingresso "Resampling" e ne stampa l'indice.
Serve a resample_scenes.py per misurare dentro Live (ASIO: loopback Windows muto).

Uso: python add_resampling_track.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lom_direct import Lom  # noqa: E402


def main():
    lom = Lom(timeout=30)
    lom.call([], "create_audio_track", [-1])
    idx = lom.length(["tracks"]) - 1
    tr = ["tracks:%d" % idx]
    # La lista contiene tutte le tracce del set (centinaia): "Resampling" sta in testa,
    # quindi cerco solo nelle prime voci invece di leggerle tutte (lentissimo).
    ri = next(i for i in range(5)
              if lom.get(tr + ["available_input_routing_types:%d" % i], "display_name") == "Resampling")
    lom.send({"cmd": "link", "root": "song", "path": tr, "prop": "input_routing_type",
              "value_path": tr + ["available_input_routing_types:%d" % ri]})
    lom.set(tr, "current_monitoring_state", 2)
    lom.set(tr, "arm", True)
    got = lom.get(tr + ["input_routing_type"], "display_name")
    assert got == "Resampling", got
    print(idx)


if __name__ == "__main__":
    main()
