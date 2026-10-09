import logging

from flask import Blueprint, current_app, request

from services.voice_service import VoiceUnavailable
from utils.auth import get_owned_session, require_auth
from utils.errors import AppError, ok
from utils.logging_config import log_event

bp = Blueprint("voice", __name__, url_prefix="/api/voice")
log = logging.getLogger(__name__)
ALLOWED = {".webm", ".wav", ".mp3", ".m4a", ".ogg", ".mp4"}


@bp.get("/status")
def status():
    return ok(current_app.extensions["services"].voice.status())


@bp.post("/transcribe")
@require_auth
def transcribe():
    get_owned_session(request.form.get("session_id", ""))
    f = request.files.get("audio")
    if not f:
        raise AppError("validation_error", "No audio file was provided.", 400)
    name = (f.filename or "audio.webm").lower()
    suffix = next((e for e in ALLOWED if name.endswith(e)), ".webm")
    limit = current_app.config["MAX_AUDIO_MB"] * 1024 * 1024
    audio = f.read(limit + 1)
    if len(audio) > limit:
        raise AppError("file_too_large", "Audio recording is too large.", 413)
    if len(audio) < 1000:
        raise AppError("audio_too_short", "The recording was too short to transcribe.", 422)
    try:
        result = current_app.extensions["services"].voice.transcribe(audio, suffix)
    except VoiceUnavailable as e:
        raise AppError("stt_unavailable", "Server-side speech recognition is unavailable. Use browser captions or type your answer.", 503, {"hint": str(e)})
    log_event(log, "transcription_completed", words=len(result["text"].split()))
    return ok(result)
