"""Approximate gaze / attention classification from head pose (and iris position when available).

IMPORTANT: these are coarse, approximate heuristics - not scientific gaze tracking, and
looking away is NOT evidence of dishonesty (people think, glance at notes they are allowed to use,
adjust their seat, have off-axis cameras, ...).
"""
from __future__ import annotations

YAW_LIMIT = 25.0     # degrees left/right treated as "toward screen"
PITCH_UP = 20.0
PITCH_DOWN = -25.0   # cameras sit above the screen, so glancing slightly down is normal
IRIS_CENTER = (0.35, 0.65)

GAZE_LABELS = ["center", "left", "right", "up", "down", "face_missing", "insufficient_data"]


def classify_gaze(yaw: float | None, pitch: float | None, iris_h: float | None = None) -> str:
    """Return one of center/left/right/up/down. Head pose dominates; iris ratio refines 'center'."""
    if yaw is None:
        return "insufficient_data"
    if yaw > YAW_LIMIT:
        return "right"
    if yaw < -YAW_LIMIT:
        return "left"
    if pitch is not None:
        if pitch > PITCH_UP:
            return "up"
        if pitch < PITCH_DOWN:
            return "down"
    if iris_h is not None and not (IRIS_CENTER[0] <= iris_h <= IRIS_CENTER[1]):
        return "right" if iris_h > IRIS_CENTER[1] else "left"
    return "center"


def is_toward_screen(label: str) -> bool:
    return label == "center"


def screen_attention_ratio(attentive_samples: int, valid_face_samples: int) -> float | None:
    """Approximate share of valid face-detected time spent looking toward the screen (0-1)."""
    if valid_face_samples <= 0:
        return None
    return round(attentive_samples / valid_face_samples, 3)
