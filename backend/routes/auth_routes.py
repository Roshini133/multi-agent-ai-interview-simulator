from flask import Blueprint, g
from werkzeug.security import check_password_hash, generate_password_hash

from database import db
from models import Candidate, User
from utils.auth import issue_token, require_auth
from utils.errors import AppError, ok
from utils.logging_config import log_event
from utils.validation import EMAIL_RE, json_body, require_str
import logging

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
log = logging.getLogger(__name__)


@bp.post("/register")
def register():
    data = json_body()
    name = require_str(data, "name", 80, 2)
    email = require_str(data, "email", 255).lower()
    password = data.get("password") or ""
    if not EMAIL_RE.match(email):
        raise AppError("validation_error", "Please enter a valid email address.", 400)
    if not isinstance(password, str) or not (8 <= len(password) <= 128):
        raise AppError("validation_error", "Password must be 8-128 characters.", 400)
    if User.query.filter_by(email=email).first():
        raise AppError("email_taken", "An account with this email already exists.", 409)
    user = User(name=name, email=email, password_hash=generate_password_hash(password))
    user.candidate = Candidate(full_name=name)
    db.session.add(user)
    db.session.commit()
    log_event(log, "user_registered", user_id=user.id)
    return ok({"token": issue_token(user), "user": user.to_dict()}, 201)


@bp.post("/login")
def login():
    data = json_body()
    email = require_str(data, "email", 255).lower()
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, str(data.get("password") or "")):
        raise AppError("invalid_credentials", "Incorrect email or password.", 401)
    return ok({"token": issue_token(user), "user": user.to_dict()})


@bp.get("/me")
@require_auth
def me():
    return ok({"user": g.user.to_dict()})
