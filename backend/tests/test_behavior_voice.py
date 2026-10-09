import io

import cv2
import numpy as np

from services.behavioral_analysis import BehaviorMonitor, summarize_integrity
from services.gaze_analysis import classify_gaze, screen_attention_ratio
from services.voice_service import speech_metrics


def obs(faces=1, gaze="center", yaw=0.0):
    if faces == 0:
        return {"insufficient": False, "face_count": 0, "face_detected": False, "gaze": "face_missing", "looking_at_screen": None}
    return {"insufficient": False, "face_count": faces, "face_detected": True, "gaze": gaze, "looking_at_screen": gaze == "center", "yaw": yaw}


def test_classify_gaze():
    assert classify_gaze(0, 0) == "center"
    assert classify_gaze(40, 0) == "right" and classify_gaze(-40, 0) == "left"
    assert classify_gaze(0, 30) == "up" and classify_gaze(0, -40) == "down"
    assert classify_gaze(None, None) == "insufficient_data"
    assert screen_attention_ratio(8, 10) == 0.8 and screen_attention_ratio(0, 0) is None


def test_monitor_events_and_ratio():
    m = BehaviorMonitor(3.0, 4.0)
    counters, events = None, []
    for t in range(0, 20):  # looking away from t=0..9, face missing t=10..14, multi at 16
        o = obs(1, "left") if t < 10 else obs(0) if t < 15 else obs(2) if t == 16 else obs(1)
        counters, ev = m.ingest("s", o, float(t), counters)
        events += ev
    types = [e["type"] for e in events]
    assert types.count("extended_off_screen_gaze") == 1 and types.count("face_absent") == 1 and types.count("multiple_faces") == 1
    assert counters["samples"] == 20 and counters["screen_attention_ratio"] is not None


def test_integrity_wording_is_neutral():
    counters = {"samples": 100, "face_samples": 90, "attentive_samples": 60, "screen_attention_ratio": 0.667, "gaze_counts": {}}
    events = [{"event_type": "extended_off_screen_gaze"}] * 3 + [{"event_type": "face_absent"}]
    s = summarize_integrity(counters, events)
    text = " ".join(s["observations"] + [s["disclaimer"]]).lower()
    assert "repeated off-screen gaze" in text and "not evidence of" in text
    assert "cheat" not in " ".join(s["observations"]).lower() and "lying" not in text
    assert "insufficient visual data" in summarize_integrity({"samples": 2}, [])["observations"][0].lower()


def test_behavior_api(client, auth, session_id):
    img = np.full((240, 320, 3), 127, np.uint8)
    img[::2] = 90
    jpg = cv2.imencode(".jpg", img)[1].tobytes()
    # not active yet -> clean 409
    r = client.post("/api/behavior/analyze", headers=auth, data={"session_id": session_id, "frame": (io.BytesIO(jpg), "f.jpg")}, content_type="multipart/form-data")
    assert r.status_code == 409
    client.post("/api/interview/question", json={"session_id": session_id}, headers=auth)
    r = client.post("/api/behavior/analyze", headers=auth, data={"session_id": session_id, "frame": (io.BytesIO(jpg), "f.jpg")}, content_type="multipart/form-data")
    assert r.status_code == 200 and r.json["data"]["observation"]["face_detected"] is False
    assert client.post("/api/behavior/event", headers=auth, json={"session_id": session_id, "type": "tab_hidden"}).json["data"]["recorded"] is True
    assert client.post("/api/behavior/event", headers=auth, json={"session_id": session_id, "type": "hack"}).status_code == 400
    summ = client.get(f"/api/behavior/{session_id}/summary", headers=auth).json["data"]
    assert next(s for s in summ["signals"] if s["type"] == "browser_focus_change")["count"] == 1


def test_speech_metrics():
    m = speech_metrics("Um, I actually like building things, you know, basically APIs.", 6, [0.4, 1.5, 2.2])
    assert m["word_count"] == 10 and m["filler_count"] >= 4 and m["words_per_minute"] == 100
    assert m["pause_count"] == 2 and m["longest_pause_seconds"] == 2.2


def test_transcribe_unavailable_is_503_with_clean_message(client, auth, session_id):
    r = client.post("/api/voice/transcribe", headers=auth, data={"session_id": session_id, "audio": (io.BytesIO(b"0" * 5000), "a.webm")}, content_type="multipart/form-data")
    assert r.status_code == 503 and r.json["error"]["code"] == "stt_unavailable"


def test_system_status(client):
    d = client.get("/api/system/status").json["data"]
    assert d["llm"]["available"] is False and d["vision"]["available"] is True
