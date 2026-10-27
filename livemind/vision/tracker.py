"""HandTracker: webcam + MediaPipe Hand Landmarker (Tasks API, mediapipe >= 0.10.9).

La vecchia mp.solutions e' stata rimossa nelle versioni recenti: qui si usa
HandLandmarker in modalita' VIDEO. Il modello .task viene scaricato al primo avvio.
"""
from __future__ import annotations
import os
import pathlib
import urllib.request

# silenzia i log interni di MediaPipe/TFLite (W0000, INFO XNNPACK)
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

try:
    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    _HAS_VISION = True
except ImportError:  # pragma: no cover
    _HAS_VISION = False

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
             "hand_landmarker/float16/1/hand_landmarker.task")

# connessioni scheletro mano (indici landmark) per il disegno
_CONNECTIONS = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
                (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15),
                (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]


class HandTracker:
    def __init__(self, camera_index: int = 0, max_hands: int = 2,
                 min_detection_confidence: float = 0.6):
        if not _HAS_VISION:
            raise RuntimeError("pip install opencv-python mediapipe")
        model_path = pathlib.Path(__file__).parent / "hand_landmarker.task"
        if not model_path.exists():
            print("[vision] scarico il modello hand_landmarker (una tantum)...")
            urllib.request.urlretrieve(MODEL_URL, model_path)
        options = mp_vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_tracking_confidence=0.5)
        self.landmarker = mp_vision.HandLandmarker.create_from_options(options)
        self.cap = cv2.VideoCapture(camera_index)
        self._ts_ms = 0

    def read(self, draw: bool = True):
        """Ritorna (frame_bgr, {"left": [(x,y)...], "right": [...]}) o (None, {})."""
        ok, frame = self.cap.read()
        if not ok:
            return None, {}
        frame = cv2.flip(frame, 1)  # specchio: piu' naturale
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        self._ts_ms += 33
        res = self.landmarker.detect_for_video(mp_img, self._ts_ms)
        hands: dict[str, list[tuple[float, float]]] = {}
        h, w = frame.shape[:2]
        for lms, handed in zip(res.hand_landmarks, res.handedness):
            label = handed[0].category_name.lower()  # "left"/"right"
            pts = [(p.x, p.y) for p in lms]
            hands[label] = pts
            if draw:
                px = [(int(x * w), int(y * h)) for x, y in pts]
                for a, b in _CONNECTIONS:
                    cv2.line(frame, px[a], px[b], (0, 200, 100), 2)
                for p in px:
                    cv2.circle(frame, p, 3, (0, 255, 160), -1)
        return frame, hands

    def close(self):
        self.cap.release()
        self.landmarker.close()
