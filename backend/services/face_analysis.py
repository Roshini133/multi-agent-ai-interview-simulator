"""Per-frame face analysis, run locally (no frames are stored or sent to the LLM).

Backends (chosen automatically):
1. MediaPipe FaceLandmarker (Tasks API) - if the ``face_landmarker.task`` model file exists.
   Gives face count, landmark-based head yaw/pitch and iris position.
2. OpenCV Haar cascades - always available with opencv. Gives face count and a much cruder
   head-turn estimate. Flagged with quality="low".

All outputs are *observed signals*, deliberately free of any claim about honesty or emotion.
"""
from __future__ import annotations

import logging
import math
import os

import cv2
import numpy as np

from services.gaze_analysis import classify_gaze, is_toward_screen

log = logging.getLogger(__name__)


class FaceAnalyzer:
    def __init__(self, enabled: bool = True, mediapipe_model_path: str | None = None):
        self.enabled = enabled
        self.backend = "disabled"
        self._landmarker = None
        self._cascades: dict[str, cv2.CascadeClassifier] = {}
        if not enabled:
            return
        if mediapipe_model_path and os.path.exists(mediapipe_model_path):
            try:
                import mediapipe as mp
                from mediapipe.tasks import python as mp_python
                from mediapipe.tasks.python import vision
                options = vision.FaceLandmarkerOptions(
                    base_options=mp_python.BaseOptions(model_asset_path=mediapipe_model_path),
                    running_mode=vision.RunningMode.IMAGE, num_faces=3)
                self._landmarker = vision.FaceLandmarker.create_from_options(options)
                self._mp = mp
                self.backend = "mediapipe-face-landmarker"
            except Exception as e:  # noqa: BLE001
                log.warning("mediapipe_init_failed: %s", type(e).__name__)
        if self._landmarker is None:
            base = cv2.data.haarcascades
            for name, f in (("front", "haarcascade_frontalface_default.xml"), ("profile", "haarcascade_profileface.xml"), ("eye", "haarcascade_eye.xml")):
                c = cv2.CascadeClassifier(os.path.join(base, f))
                if not c.empty():
                    self._cascades[name] = c
            self.backend = "opencv-haar" if "front" in self._cascades else "disabled"

    def status(self) -> dict:
        return {"available": self.backend != "disabled", "backend": self.backend,
                "quality": "medium" if self.backend.startswith("mediapipe") else "low" if self.backend == "opencv-haar" else "none"}

    # ---------------------------------------------------------------------------------
    def analyze(self, image_bytes: bytes) -> dict:
        """Analyse a JPEG/PNG frame. Returns a compact observation dict."""
        if self.backend == "disabled":
            return self._obs(insufficient=True, reason="vision_disabled")
        frame = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if frame is None or frame.size == 0:
            return self._obs(insufficient=True, reason="bad_frame")
        h, w = frame.shape[:2]
        if w > 480:
            frame = cv2.resize(frame, (480, int(h * 480 / w)))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if float(gray.mean()) < 25 or float(gray.std()) < 8:  # too dark / covered / flat
            return self._obs(insufficient=True, reason="low_light_or_covered")
        return self._mediapipe(frame) if self._landmarker else self._haar(gray)

    # -------------------------------------------------------------------- mediapipe
    def _mediapipe(self, bgr: np.ndarray) -> dict:
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        result = self._landmarker.detect(self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb))
        faces = result.face_landmarks or []
        if not faces:
            return self._obs(face_count=0, backend=self.backend)
        lm = faces[0]
        pt = lambda i: np.array([lm[i].x, lm[i].y])
        nose, left_cheek, right_cheek = pt(1), pt(234), pt(454)
        d_l, d_r = np.linalg.norm(nose - left_cheek), np.linalg.norm(nose - right_cheek)
        yaw = float((d_l - d_r) / max(d_l + d_r, 1e-6)) * 90.0        # + = turned to the (image) right
        eye_y = (pt(33)[1] + pt(263)[1]) / 2
        chin_y = pt(152)[1]
        ratio = (nose[1] - eye_y) / max(chin_y - eye_y, 1e-6)          # ~0.45 when facing the camera
        pitch = float((0.45 - ratio) * 160.0)                           # + = looking up
        iris_h = None
        if len(lm) >= 478:  # iris landmarks present
            def ratio_h(iris, outer, inner):
                o, i, c = pt(outer)[0], pt(inner)[0], pt(iris)[0]
                return (c - o) / (i - o) if abs(i - o) > 1e-6 else 0.5
            iris_h = float((ratio_h(468, 33, 133) + ratio_h(473, 362, 263)) / 2)
        gaze = classify_gaze(yaw, pitch, iris_h)
        return self._obs(face_count=len(faces), yaw=yaw, pitch=pitch, gaze=gaze, backend=self.backend, quality="medium")

    # -------------------------------------------------------------------------- haar
    def _haar(self, gray: np.ndarray) -> dict:
        gray = cv2.equalizeHist(gray)
        H, W = gray.shape
        min_size = (max(40, W // 10), max(40, W // 10))
        faces = self._cascades["front"].detectMultiScale(gray, 1.1, 5, minSize=min_size)
        if len(faces) == 0 and "profile" in self._cascades:
            side = self._cascades["profile"].detectMultiScale(gray, 1.1, 4, minSize=min_size)
            flipped = self._cascades["profile"].detectMultiScale(cv2.flip(gray, 1), 1.1, 4, minSize=min_size)
            if len(side) or len(flipped):  # profile face => head clearly turned
                return self._obs(face_count=1, yaw=(40.0 if len(side) else -40.0), pitch=0.0, gaze="right" if len(side) else "left", backend=self.backend, quality="low")
            return self._obs(face_count=0, backend=self.backend, quality="low")
        # main (largest) face
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        # Ignore small secondary detections (typical Haar false positives) when counting faces.
        faces = [f for f in faces if f[2] * f[3] >= 0.4 * w * h]
        if len(faces) > 1 and "eye" in self._cascades:  # secondary faces must show at least one eye
            verified = [f for f in faces if len(self._cascades["eye"].detectMultiScale(gray[f[1]:f[1] + f[3] // 2 + f[3] // 8, f[0]:f[0] + f[2]], 1.1, 5, minSize=(f[2] // 8, f[2] // 8))) >= 1]
            faces = verified or [(x, y, w, h)]
        yaw, pitch = 0.0, 0.0
        cx = (x + w / 2) / W
        yaw += (cx - 0.5) * 30.0  # weak cue: far off-centre in frame
        eyes = self._cascades["eye"].detectMultiScale(gray[y:y + h // 2 + h // 8, x:x + w], 1.1, 6, minSize=(w // 8, w // 8)) if "eye" in self._cascades else []
        if len(eyes) >= 2:
            eyes = sorted(eyes, key=lambda e: e[0])
            mid = ((eyes[0][0] + eyes[0][2] / 2) + (eyes[-1][0] + eyes[-1][2] / 2)) / 2 / w
            yaw += (mid - 0.5) * 120.0
            eye_line = np.mean([e[1] + e[3] / 2 for e in eyes]) / h
            pitch = (0.36 - eye_line) * 200.0
        elif len(eyes) == 1:
            yaw += 22.0 * (1 if (eyes[0][0] + eyes[0][2] / 2) / w < 0.5 else -1)  # one eye visible => head turned
        gaze = classify_gaze(yaw, pitch)
        return self._obs(face_count=len(faces), yaw=float(yaw), pitch=float(pitch), gaze=gaze, backend=self.backend, quality="low")

    # --------------------------------------------------------------------- helpers
    @staticmethod
    def _obs(face_count: int = 0, yaw=None, pitch=None, gaze=None, backend="", quality="low", insufficient=False, reason=None) -> dict:
        if insufficient:
            return {"insufficient": True, "reason": reason, "face_count": 0, "face_detected": False, "gaze": "insufficient_data", "looking_at_screen": None,
                    "label": "Insufficient visual data", "backend": backend}
        if face_count == 0:
            return {"insufficient": False, "face_count": 0, "face_detected": False, "gaze": "face_missing", "looking_at_screen": None,
                    "label": "Face not detected", "backend": backend, "quality": quality}
        toward = is_toward_screen(gaze)
        label = "Multiple faces detected" if face_count > 1 else ("Looking toward screen" if toward else "Looking away from screen")
        return {"insufficient": False, "face_count": face_count, "face_detected": True, "yaw": round(yaw, 1) if yaw is not None else None,
                "pitch": round(pitch, 1) if pitch is not None else None, "gaze": gaze, "looking_at_screen": toward, "label": label,
                "backend": backend, "quality": quality}
