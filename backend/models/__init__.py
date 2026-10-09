"""ORM models. Uses only portable column types (JSON works on SQLite and PostgreSQL)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from database import db


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=_now)
    candidate = db.relationship("Candidate", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sessions = db.relationship("InterviewSession", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {"id": self.id, "email": self.email, "name": self.name}


class Candidate(db.Model):
    __tablename__ = "candidates"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    target_role = db.Column(db.String(60))
    created_at = db.Column(db.DateTime, default=_now)
    user = db.relationship("User", back_populates="candidate")


class InterviewSession(db.Model):
    __tablename__ = "interview_sessions"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    role = db.Column(db.String(60), nullable=False)
    status = db.Column(db.String(20), default="created", nullable=False)  # created|active|completed
    active_agent = db.Column(db.String(20))
    difficulty = db.Column(db.String(10), default="MEDIUM")
    created_at = db.Column(db.DateTime, default=_now)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)
    state = db.Column(db.JSON, default=dict)             # orchestrator state (difficulty per agent, adaptation log, ...)
    behavior_summary = db.Column(db.JSON, default=dict)  # aggregated webcam counters
    settings = db.Column(db.JSON, default=dict)

    user = db.relationship("User", back_populates="sessions")
    resume = db.relationship("ResumeData", back_populates="session", uselist=False, cascade="all, delete-orphan")
    questions = db.relationship("Question", back_populates="session", order_by="Question.index", cascade="all, delete-orphan")
    events = db.relationship("BehavioralEvent", back_populates="session", order_by="BehavioralEvent.id", cascade="all, delete-orphan")
    report = db.relationship("FinalReport", back_populates="session", uselist=False, cascade="all, delete-orphan")


class ResumeData(db.Model):
    __tablename__ = "resume_data"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey("interview_sessions.id"), unique=True, nullable=False)
    filename = db.Column(db.String(255))
    raw_text = db.Column(db.Text)
    parsed = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=_now)
    session = db.relationship("InterviewSession", back_populates="resume")


class Question(db.Model):
    __tablename__ = "questions"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey("interview_sessions.id"), nullable=False, index=True)
    index = db.Column(db.Integer, nullable=False)          # global order in the interview
    agent = db.Column(db.String(20), nullable=False)       # hr | technical | manager
    text = db.Column(db.Text, nullable=False)
    topic = db.Column(db.String(120))
    difficulty = db.Column(db.String(10))
    source = db.Column(db.String(20), default="llm")       # llm | fallback
    resume_grounded = db.Column(db.Boolean, default=False)
    intro = db.Column(db.Text)                             # spoken hand-over line, if any
    created_at = db.Column(db.DateTime, default=_now)
    session = db.relationship("InterviewSession", back_populates="questions")
    answer = db.relationship("Answer", back_populates="question", uselist=False, cascade="all, delete-orphan")


class Answer(db.Model):
    __tablename__ = "answers"
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), unique=True, nullable=False)
    session_id = db.Column(db.String(36), db.ForeignKey("interview_sessions.id"), nullable=False, index=True)
    text = db.Column(db.Text, nullable=False)
    input_mode = db.Column(db.String(10), default="text")  # text | voice
    duration_seconds = db.Column(db.Float)
    speech_metrics = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=_now)
    question = db.relationship("Question", back_populates="answer")
    evaluation = db.relationship("Evaluation", back_populates="answer", uselist=False, cascade="all, delete-orphan")


class Evaluation(db.Model):
    __tablename__ = "evaluations"
    id = db.Column(db.Integer, primary_key=True)
    answer_id = db.Column(db.Integer, db.ForeignKey("answers.id"), unique=True, nullable=False)
    scores = db.Column(db.JSON, default=dict)
    overall = db.Column(db.Float)
    feedback = db.Column(db.Text)
    improvement = db.Column(db.Text)
    method = db.Column(db.String(30))  # llm+heuristic | heuristic
    created_at = db.Column(db.DateTime, default=_now)
    answer = db.relationship("Answer", back_populates="evaluation")


class BehavioralEvent(db.Model):
    __tablename__ = "behavioral_events"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey("interview_sessions.id"), nullable=False, index=True)
    event_type = db.Column(db.String(40), nullable=False)
    detail = db.Column(db.String(255))
    offset_seconds = db.Column(db.Float)   # seconds since interview start
    duration_seconds = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=_now)
    session = db.relationship("InterviewSession", back_populates="events")


class FinalReport(db.Model):
    __tablename__ = "final_reports"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey("interview_sessions.id"), unique=True, nullable=False)
    content = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=_now)
    session = db.relationship("InterviewSession", back_populates="report")
