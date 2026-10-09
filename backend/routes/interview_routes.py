import logging

from flask import Blueprint, current_app, g

from database import db
from models import Evaluation, InterviewSession
from utils.auth import get_owned_session, require_auth
from utils.errors import AppError, ok
from utils.roles import ROLES, role_label
from utils.validation import clean_text, json_body, require_str

bp = Blueprint("interview", __name__, url_prefix="/api/interview")
log = logging.getLogger(__name__)


def _svc():
    return current_app.extensions["services"]


def _summary(s: InterviewSession) -> dict:
    orch = _svc().orchestrator
    pending = s.questions[-1] if s.questions and s.questions[-1].answer is None else None
    dash_score = None
    if s.report:
        dash_score = (s.report.content.get("scores") or {}).get("overall")
    return {"session_id": s.id, "role": s.role, "role_label": role_label(s.role), "status": s.status, "active_agent": s.active_agent,
            "difficulty": s.difficulty, "created_at": s.created_at.isoformat(), "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None, "duration_seconds": orch.duration_seconds(s) if s.started_at else 0,
            "questions_asked": len(s.questions), "questions_answered": sum(1 for q in s.questions if q.answer), "total_questions": orch.total_questions,
            "has_resume": bool(s.resume), "pending_question_id": pending.id if pending else None, "overall_score": dash_score,
            "plan": [{"agent": a, "count": n} for a, n in orch.plan]}


@bp.get("/roles")
def roles():
    return ok({"roles": [{"key": k, "label": v["label"]} for k, v in ROLES.items()]})


@bp.get("/")
@require_auth
def list_sessions():
    sessions = InterviewSession.query.filter_by(user_id=g.user.id).order_by(InterviewSession.created_at.desc()).limit(50).all()
    return ok({"sessions": [_summary(s) for s in sessions]})


@bp.post("/start")
@require_auth
def start():
    data = json_body()
    role = require_str(data, "role", 60)
    s = _svc().orchestrator.create_session(g.user, role, {"input_preference": data.get("input_preference", "voice")})
    return ok(_summary(s), 201)


@bp.get("/<session_id>")
@require_auth
def get_session(session_id):
    return ok(_summary(get_owned_session(session_id)))


@bp.post("/question")
@require_auth
def question():
    s = get_owned_session(require_str(json_body(), "session_id", 64))
    q = _svc().orchestrator.next_question(s)
    return ok({"question": q, "finished": q is None, "session": _summary(s)})


@bp.post("/next")
@require_auth
def next_q():
    """Advance after an answer: returns the next question or ``finished: true``."""
    s = get_owned_session(require_str(json_body(), "session_id", 64))
    q = _svc().orchestrator.next_question(s)
    return ok({"question": q, "finished": q is None, "session": _summary(s)})


@bp.post("/answer")
@require_auth
def answer():
    data = json_body()
    s = get_owned_session(require_str(data, "session_id", 64))
    skipped = bool(data.get("skipped"))
    max_chars = current_app.config["MAX_ANSWER_CHARS"]
    text = clean_text(str(data.get("answer") or ""), max_chars)
    if not text and not skipped:
        raise AppError("validation_error", "Please provide an answer (or skip the question).", 400)
    qid = data.get("question_id")
    if not isinstance(qid, int):
        raise AppError("validation_error", "'question_id' must be an integer.", 400)
    dur = data.get("duration_seconds")
    dur = float(dur) if isinstance(dur, (int, float)) and 0 <= dur <= 1800 else None
    pauses = [float(p) for p in data.get("pauses", []) if isinstance(p, (int, float))][:200] if isinstance(data.get("pauses"), list) else None
    result = _svc().orchestrator.submit_answer(s, qid, text, str(data.get("input_mode", "text")), dur, pauses, skipped)
    return ok(result)


@bp.post("/evaluate")
@require_auth
def evaluate():
    data = json_body()
    s = get_owned_session(require_str(data, "session_id", 64))
    qid = data.get("question_id")
    q = next((x for x in s.questions if x.id == qid), None)
    if not q or not q.answer:
        raise AppError("not_found", "No answered question with this ID in the session.", 404)
    ev: Evaluation = q.answer.evaluation
    return ok({"question_id": q.id, "overall": ev.overall, "scores": ev.scores, "feedback": ev.feedback, "improvement": ev.improvement, "method": ev.method})


@bp.post("/<session_id>/complete")
@require_auth
def complete(session_id):
    s = get_owned_session(session_id)
    report = _svc().orchestrator.complete(s)
    return ok({"session": _summary(s), "overall": report["scores"]["overall"], "readiness": report["readiness"]})
