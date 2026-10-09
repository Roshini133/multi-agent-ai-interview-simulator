"""Database setup. SQLAlchemy keeps the code portable between SQLite and PostgreSQL."""
from pathlib import Path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm.attributes import flag_modified

db = SQLAlchemy()


def init_db(app: Flask) -> None:
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if uri.startswith("sqlite:///") and ":memory:" not in uri:
        Path(uri.replace("sqlite:///", "", 1)).parent.mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    with app.app_context():
        from models import (  # noqa: F401  (register models)
            Answer, BehavioralEvent, Candidate, Evaluation, FinalReport,
            InterviewSession, Question, ResumeData, User,
        )
        db.create_all()


def json_set(obj, attr: str, value) -> None:
    """Assign a JSON column and force change tracking (in-place mutation is not detected)."""
    setattr(obj, attr, value)
    flag_modified(obj, attr)
