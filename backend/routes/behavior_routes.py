import base64
import logging

from flask import Blueprint, current_app, request

from database import db, json_set
from models import BehavioralEvent
from services.behavioral_analysis import CLIENT_EVENTS, summarize_integrity
from utils.auth import get_owned_session, require_auth
from utils.errors import AppError, ok
from utils.logging_config import log_event
from utils.validation import json_body

bp = Blueprint("behavior", __name__, url_prefix="/api/behavior")
log = logging.getLogger(__name__)


def _offset(session) -> float:
    from datetime import datetime, timezone
    if not session.started_at:
        return 0.0
    return max(0.0, (datetime.now(timezone.utc).replace(tzinfo=None) - session.started_at).total_seconds())


@bp.get("/status")
def status():
    return ok(current_app.extensions["services"].face.status())


@bp.post("/analyze")
@require_auth
def analyze():
    """Analyse ONE webcam frame locally. The frame is processed in memory and discarded."""
    svc = current_app.extensions["services"]
    if request.files.get("frame"):
        session = get_owned_session(request.form.get("session_id", ""))
        raw = request.files["frame"].read(current_app.config["MAX_FRAME_KB"] * 1024 + 1)
    else:
        data = json_body()
        session = get_owned_session(str(data.get("session_id", "")))
        try:
            raw = base64.b64decode(str(data.get("image", "")).split(",")[-1], validate=False)
        except ValueError:
            raise AppError("validation_error", "Invalid image data.", 400)
    if len(raw) > current_app.config["MAX_FRAME_KB"] * 1024:
        raise AppError("file_too_large", "Frame too large.", 413)
    if session.status != "active":
        raise AppError("interview_not_active", "Behavioural analysis is only recorded during an active interview.", 409)
    obs = svc.face.analyze(raw)
    t = _offset(session)
    counters, events = svc.monitor.ingest(session.id, obs, t, session.behavior_summary)
    json_set(session, "behavior_summary", counters)
    for e in events:
        db.session.add(BehavioralEvent(session_id=session.id, event_type=e["type"], detail=e["detail"], offset_seconds=round(t, 1), duration_seconds=e["duration"]))
        log_event(log, "behavior_event", session_id=session.id, type=e["type"])
    db.session.commit()
    return ok({"observation": obs, "new_events": events, "screen_attention_ratio": counters.get("screen_attention_ratio")})


@bp.post("/event")
@require_auth
def client_event():
    data = json_body()
    session = get_owned_session(str(data.get("session_id", "")))
    kind = CLIENT_EVENTS.get(str(data.get("type", "")))
    if not kind:
        raise AppError("validation_error", "Unsupported event type.", 400)
    if session.status == "active":
        db.session.add(BehavioralEvent(session_id=session.id, event_type=kind, detail=str(data["type"]).replace("_", " "), offset_seconds=round(_offset(session), 1), duration_seconds=0))
        db.session.commit()
    return ok({"recorded": session.status == "active"})


@bp.get("/<session_id>/summary")
@require_auth
def summary(session_id):
    s = get_owned_session(session_id)
    return ok(summarize_integrity(s.behavior_summary, s.events))
