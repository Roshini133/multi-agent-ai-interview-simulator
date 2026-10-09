"""AI Interview Simulator - Flask application factory.

Run locally:  python app.py         (development server)
Production:   gunicorn -w 2 -b 0.0.0.0:5000 "app:create_app()"
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from flask import Flask
from flask_cors import CORS

from config import Config
from database import init_db
from routes import register_blueprints
from services.answer_evaluator import AnswerEvaluator
from services.behavioral_analysis import BehaviorMonitor
from services.embedding_service import EmbeddingService
from services.face_analysis import FaceAnalyzer
from services.interview_orchestrator import InterviewOrchestrator
from services.ollama_service import OllamaService
from services.session_manager import SessionManager
from services.voice_service import VoiceService
from utils.errors import register_error_handlers
from utils.logging_config import setup_logging


@dataclass
class Services:
    llm: OllamaService
    embeddings: EmbeddingService
    voice: VoiceService
    face: FaceAnalyzer
    monitor: BehaviorMonitor
    sessions: SessionManager
    orchestrator: InterviewOrchestrator


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)
    setup_logging(app.config["LOG_LEVEL"])
    log = logging.getLogger("app")
    if not app.config.get("SECRET_KEY_FROM_ENV") and not app.config["TESTING"]:
        log.warning("SECRET_KEY not set - using a random key; logins reset on restart. Set SECRET_KEY in .env")

    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}}, supports_credentials=False)
    init_db(app)
    register_error_handlers(app)

    cfg = app.config
    llm = OllamaService.from_config(cfg)
    embeddings = EmbeddingService(cfg["EMBEDDINGS_ENABLED"], cfg["EMBEDDING_MODEL"])
    sessions = SessionManager(llm, embeddings)
    evaluator = AnswerEvaluator(llm, embeddings)
    app.extensions["services"] = Services(
        llm=llm, embeddings=embeddings, sessions=sessions,
        voice=VoiceService(cfg["WHISPER_ENABLED"], cfg["WHISPER_MODEL"], cfg["WHISPER_COMPUTE_TYPE"]),
        face=FaceAnalyzer(cfg["VISION_ENABLED"], cfg["MEDIAPIPE_FACE_MODEL"]),
        monitor=BehaviorMonitor(cfg["FACE_ABSENT_SECONDS"], cfg["OFF_SCREEN_SECONDS"]),
        orchestrator=InterviewOrchestrator(cfg, sessions, evaluator, embeddings))
    register_blueprints(app)

    @app.get("/")
    def index():
        return {"message": "AI Interview Simulator API", "docs": "/api/health"}

    return app


if __name__ == "__main__":
    import os
    create_app().run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "5000")), debug=Config.DEBUG)
