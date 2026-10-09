"""Signed-token authentication (itsdangerous) and password hashing (werkzeug)."""
from __future__ import annotations

import functools

from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from database import db
from models import InterviewSession, User
from utils.errors import AppError


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="auth-token")


def issue_token(user: User) -> str:
    return _serializer().dumps({"uid": user.id})


def require_auth(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise AppError("unauthorized", "Please sign in to continue.", 401)
        try:
            data = _serializer().loads(header[7:], max_age=current_app.config["TOKEN_MAX_AGE_SECONDS"])
        except SignatureExpired:
            raise AppError("token_expired", "Your login has expired. Please sign in again.", 401)
        except BadSignature:
            raise AppError("unauthorized", "Invalid authentication token.", 401)
        user = db.session.get(User, data.get("uid"))
        if not user:
            raise AppError("unauthorized", "Account not found.", 401)
        g.user = user
        return fn(*args, **kwargs)

    return wrapper


def get_owned_session(session_id: str) -> InterviewSession:
    """Fetch a session that belongs to the current user or raise a clean 404 / 403."""
    if not session_id or len(session_id) > 64:
        raise AppError("invalid_session", "Invalid session ID.", 404)
    session = db.session.get(InterviewSession, session_id)
    if not session:
        raise AppError("invalid_session", "Interview session not found or expired.", 404)
    if session.user_id != g.user.id:
        raise AppError("forbidden", "You do not have access to this interview session.", 403)
    return session
