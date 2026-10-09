from flask import Blueprint, current_app, request
from werkzeug.utils import secure_filename

from services.resume_parser import extract_text, parse_resume
from utils.auth import get_owned_session, require_auth
from utils.errors import AppError, ok

bp = Blueprint("resume", __name__, url_prefix="/api/resume")


@bp.post("/upload")
@require_auth
def upload():
    session = get_owned_session(request.form.get("session_id", ""))
    f = request.files.get("file")
    if not f or not f.filename:
        raise AppError("validation_error", "Please choose a PDF file to upload.", 400)
    filename = secure_filename(f.filename) or "resume.pdf"
    if not filename.lower().endswith(".pdf") or (f.mimetype and f.mimetype not in ("application/pdf", "application/octet-stream", "application/x-pdf")):
        raise AppError("invalid_file", "Only PDF resumes are supported.", 400)
    limit = current_app.config["MAX_RESUME_MB"] * 1024 * 1024
    data = f.read(limit + 1)
    if len(data) > limit:
        raise AppError("file_too_large", f"Resume must be smaller than {current_app.config['MAX_RESUME_MB']} MB.", 413)
    text = extract_text(data)
    parsed = parse_resume(text)
    current_app.extensions["services"].orchestrator.attach_resume(session, filename, text, parsed)
    return ok({"filename": filename, "parsed": parsed}, 201)


@bp.get("/<session_id>")
@require_auth
def get_resume(session_id):
    s = get_owned_session(session_id)
    if not s.resume:
        raise AppError("not_found", "No resume uploaded for this session.", 404)
    return ok({"filename": s.resume.filename, "parsed": s.resume.parsed})
