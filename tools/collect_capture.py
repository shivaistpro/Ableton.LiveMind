"""Dopo resample_scenes.py: cancella le clip registrate (Live cosi' rilascia i file),
copia i wav in out/<cartella> e scrive out/<cartella>_files.json per eq_check/eq_plan.

Uso: python collect_capture.py <piano.json> <indice traccia rec> <cartella>
"""
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lom_direct import Lom  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")


def main(plan_path, rec, folder):
    status = json.load(open(os.path.join(OUT, "resample_status.json")))
    assert status["state"] == "finito", status["state"]
    lom = Lom(timeout=30)
    for _, scene in json.load(open(plan_path)):
        lom.call(["tracks:%d" % rec, "clip_slots:%d" % scene], "delete_clip")
    time.sleep(3)
    dst = os.path.join(OUT, folder)
    os.makedirs(dst, exist_ok=True)
    files = {}
    for label, src in status["file"].items():
        files[label] = os.path.abspath(os.path.join(dst, label + ".wav"))
        shutil.copyfile(src, files[label])
    json.dump({"file": files}, open(os.path.join(OUT, folder + "_files.json"), "w"), indent=1)
    print("copiati", len(files))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3])
