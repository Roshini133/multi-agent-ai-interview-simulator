from flask import Blueprint, current_app

from utils.errors import ok

bp = Blueprint("system", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    return ok({"status": "ok", "service": "ai-interview-simulator"})


@bp.get("/system/status")
def system_status():
    svc = current_app.extensions["services"]
    return ok({"llm": svc.llm.health(), "embeddings": {"available": svc.embeddings.is_semantic(), "backend": svc.embeddings.backend},
               "speech_to_text": svc.voice.status(), "vision": svc.face.status(),
               "plan": [{"agent": a, "count": n} for a, n in svc.orchestrator.plan]})
