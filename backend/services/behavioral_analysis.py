"""Turns per-frame observations into summarised behavioural events + integrity signals.

Design: computer vision runs locally on sparse frames (~1 per 1.5 s); only counters and
debounced *events* are stored. Nothing here labels a candidate as dishonest; all wording is neutral.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from services.gaze_analysis import screen_attention_ratio

EVENT_LABELS = {
    "multiple_faces": "Multiple faces detected",
    "face_absent": "Face not detected for an extended period",
    "extended_off_screen_gaze": "Extended off-screen gaze/head direction",
    "large_head_movement": "Large head movement",
    "browser_focus_change": "Browser tab/window focus change",
    "audio_interruption": "Audio input interruption",
}
CLIENT_EVENTS = {"tab_hidden": "browser_focus_change", "window_blur": "browser_focus_change", "audio_interruption": "audio_interruption"}

DISCLAIMER = ("These are approximate, observational signals from webcam and browser activity. They may have benign explanations "
              "(camera position, lighting, thinking, notes the candidate is permitted to use, browser notifications) and are NOT evidence of "
              "cheating or dishonesty. They are not used to reduce the interview score.")


@dataclass
class _State:
    absent_start: float | None = None
    absent_emitted: bool = False
    away_start: float | None = None
    away_emitted: bool = False
    last_multi: float = -1e9
    last_yaw: float | None = None
    last_move: float = -1e9


@dataclass
class BehaviorMonitor:
    face_absent_seconds: float = 3.0
    off_screen_seconds: float = 4.0
    _states: dict[str, _State] = field(default_factory=dict)

    def ingest(self, session_id: str, obs: dict, t: float, counters: dict | None) -> tuple[dict, list[dict]]:
        """Update counters and return (new_counters, events). ``t`` = seconds since interview start."""
        st = self._states.setdefault(session_id, _State())
        c = dict(counters or {})
        for k in ("samples", "face_samples", "attentive_samples", "insufficient_samples"):
            c.setdefault(k, 0)
        c.setdefault("gaze_counts", {})
        events: list[dict] = []
        c["samples"] += 1

        if obs.get("insufficient"):
            c["insufficient_samples"] += 1
            return self._finish(c), events

        if obs["face_count"] == 0:
            c["gaze_counts"]["face_missing"] = c["gaze_counts"].get("face_missing", 0) + 1
            st.away_start, st.away_emitted = None, False
            if st.absent_start is None:
                st.absent_start, st.absent_emitted = t, False
            if not st.absent_emitted and t - st.absent_start >= self.face_absent_seconds:
                st.absent_emitted = True
                events.append({"type": "face_absent", "detail": "Face not detected in the frame", "duration": round(t - st.absent_start, 1)})
            return self._finish(c), events

        st.absent_start, st.absent_emitted = None, False
        c["face_samples"] += 1
        g = obs.get("gaze", "center")
        c["gaze_counts"][g] = c["gaze_counts"].get(g, 0) + 1
        if obs.get("looking_at_screen"):
            c["attentive_samples"] += 1
            st.away_start, st.away_emitted = None, False
        else:
            if st.away_start is None:
                st.away_start, st.away_emitted = t, False
            if not st.away_emitted and t - st.away_start >= self.off_screen_seconds:
                st.away_emitted = True
                events.append({"type": "extended_off_screen_gaze", "detail": f"Head/gaze directed {g} of the screen", "duration": round(t - st.away_start, 1)})

        if obs["face_count"] > 1 and t - st.last_multi >= 10:
            st.last_multi = t
            events.append({"type": "multiple_faces", "detail": f"{obs['face_count']} faces detected in frame", "duration": 0})

        yaw = obs.get("yaw")
        if yaw is not None:
            if st.last_yaw is not None and abs(yaw - st.last_yaw) > 35 and t - st.last_move >= 10:
                st.last_move = t
                events.append({"type": "large_head_movement", "detail": "Sudden change in head direction", "duration": 0})
            st.last_yaw = yaw
        return self._finish(c), events

    @staticmethod
    def _finish(c: dict) -> dict:
        c["screen_attention_ratio"] = screen_attention_ratio(c["attentive_samples"], c["face_samples"])
        return c

    def forget(self, session_id: str) -> None:
        self._states.pop(session_id, None)


def summarize_integrity(counters: dict | None, events: list) -> dict:
    """Public summary used by dashboard and report. ``events`` are BehavioralEvent rows or dicts."""
    counts = {k: 0 for k in EVENT_LABELS}
    for e in events:
        t = e["event_type"] if isinstance(e, dict) else e.event_type
        counts[t] = counts.get(t, 0) + 1
    c = counters or {}
    samples, face = c.get("samples", 0), c.get("face_samples", 0)
    valid_ratio = (face / samples) if samples else None
    observations: list[str] = []
    if samples < 10:
        observations.append("Insufficient visual data: too few webcam samples were analysed to draw any observation.")
    else:
        if counts["extended_off_screen_gaze"] >= 3:
            observations.append("Repeated off-screen gaze detected during this interview.")
        if counts["face_absent"] >= 1:
            observations.append("The face was not detected for extended intervals (camera angle, lighting or leaving the frame are common causes).")
        if counts["multiple_faces"] >= 1:
            observations.append("More than one face was detected in the frame at least once.")
        if counts["browser_focus_change"] >= 1:
            observations.append("The browser tab/window lost focus during the interview.")
        if not observations:
            observations.append("No notable behavioural observations were recorded.")
    return {
        "signals": [{"type": k, "label": EVENT_LABELS[k], "count": counts[k]} for k in EVENT_LABELS],
        "screen_attention_ratio": c.get("screen_attention_ratio"),
        "attention_ratio_note": "Approximate share of face-detected time with head/gaze toward the screen. Not scientifically precise.",
        "gaze_distribution": c.get("gaze_counts", {}),
        "samples_analyzed": samples,
        "face_detected_ratio": round(valid_ratio, 3) if valid_ratio is not None else None,
        "observations": observations,
        "disclaimer": DISCLAIMER,
    }
