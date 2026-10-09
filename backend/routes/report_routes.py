from flask import Blueprint, Response, current_app

from services.report_service import build_pdf
from utils.auth import get_owned_session, require_auth
from utils.errors import AppError, ok

bp = Blueprint("report", __name__, url_prefix="/api")


def _report(session_id: str):
    s = get_owned_session(session_id)
    if not s.report:
        raise AppError("report_not_ready", "The interview must be completed before a report is available.", 409)
    return s, s.report.content


@bp.get("/report/<session_id>")
@require_auth
def report(session_id):
    return ok(_report(session_id)[1])


@bp.get("/report/<session_id>/pdf")
@require_auth
def report_pdf(session_id):
    s, content = _report(session_id)
    pdf = build_pdf(content)
    return Response(pdf, mimetype="application/pdf", headers={"Content-Disposition": f'attachment; filename="interview-report-{s.id[:8]}.pdf"'})


@bp.get("/dashboard/<session_id>")
@require_auth
def dashboard(session_id):
    s = get_owned_session(session_id)
    content = s.report.content if s.report else current_app.extensions["services"].orchestrator.dashboard(s)
    return ok(content)
