import io

import pytest
from reportlab.pdfgen import canvas

from app import create_app
from config import TestConfig
from services.ollama_service import LLMUnavailable


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def register(client, email="a@example.com", name="Asha Patel"):
    r = client.post("/api/auth/register", json={"name": name, "email": email, "password": "password123"})
    assert r.status_code == 201, r.json
    return {"Authorization": "Bearer " + r.json["data"]["token"]}


@pytest.fixture()
def auth(client):
    return register(client)


@pytest.fixture()
def session_id(client, auth):
    r = client.post("/api/interview/start", json={"role": "ai_ml_engineer"}, headers=auth)
    assert r.status_code == 201
    return r.json["data"]["session_id"]


def make_resume_pdf(lines: list[str]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for line in lines:
        c.drawString(50, y, line)
        y -= 16
    c.save()
    return buf.getvalue()


RESUME_LINES = [
    "Asha Patel", "asha.patel@example.com | +91 98765 43210", "EDUCATION", "B.Tech Computer Science (AI-ML), ABC Institute, 2026",
    "SKILLS", "Python, TensorFlow, OpenCV, SQL, Flask, React, Docker",
    "PROJECTS", "Pedestrian Crossing Intention Prediction using CNN and Bi-LSTM", "Built a real-time interview simulator using Flask and Ollama",
    "INTERNSHIPS", "Machine Learning Intern at XYZ Labs - built classification models",
    "CERTIFICATIONS", "Deep Learning Specialization - Coursera", "ACHIEVEMENTS", "Winner of college hackathon 2025",
]


@pytest.fixture()
def resume_pdf():
    return make_resume_pdf(RESUME_LINES)


class FakeLLM:
    """Stand-in for OllamaService: deterministic JSON responses, no network."""
    enabled = True
    model = "fake"

    def __init__(self):
        self.calls = 0

    def health(self):
        return {"available": True, "model": "fake"}

    def generate_json(self, system, user, required=(), **kw):
        self.calls += 1
        if "evaluator" in system:
            return {"communication": 8, "clarity": 8, "confidence": 7, "completeness": 7, "relevance": 9, "professionalism": 8,
                    "technical_accuracy": 9, "concept_understanding": 8, "problem_solving": 7, "depth": 8,
                    "situation": 8, "task": 7, "action": 8, "result": 7, "feedback": "Clear answer with a concrete example.", "improvement": "Add metrics.", "evidence": "I built"}
        if "moderator" in system:
            return {"discussion": [{"speaker": "HR", "message": "Communication was clear."}, {"speaker": "Technical", "message": "Solid fundamentals."}], "final_assessment": "Balanced, promising performance."}
        if "review" in system:
            return {"summary": "A confident performance in this round."}
        return {"question": f"Fake LLM question number {self.calls} about your experience with relevant technologies?", "topic": f"topic_{self.calls}"}

    def chat(self, *a, **k):
        raise LLMUnavailable("no")


class DownLLM(FakeLLM):
    def generate_json(self, *a, **k):
        from services.ollama_service import LLMUnavailable
        raise LLMUnavailable("down")
