import pytest

from agents.base_agent import QuestionContext
from agents.hr_agent import HRAgent
from agents.technical_agent import TechnicalAgent
from services import adaptive_questioning as adaptive
from services.answer_evaluator import AnswerEvaluator
from services.embedding_service import EmbeddingService
from services.ollama_service import OllamaService, extract_json
from tests.conftest import DownLLM, FakeLLM

emb = EmbeddingService(enabled=False)


def ctx(**kw):
    return QuestionContext(role="ai_ml_engineer", role_label="AI/ML Engineer", candidate_name="Asha Patel", **kw)


def test_hr_first_question_fallback():
    q = HRAgent("s", DownLLM(), emb).generate_question(ctx(difficulty="EASY"))
    assert q.source == "fallback" and "?" in q.text and q.topic == "introduction"


def test_hr_questions_are_not_a_fixed_script():
    agent = HRAgent("s", DownLLM(), emb)
    thin = [{"question": "q", "answer": "ok", "overall": 2.0, "topic": "introduction", "word_count": 2}]
    q = agent.generate_question(ctx(history=thin, asked_topics=["introduction"], asked_questions=["x"], number=2))
    assert q.topic == "followup"  # adapts to a thin answer
    strong = [{"question": "q", "answer": "long", "overall": 8.0, "topic": "introduction", "word_count": 90}]
    assert agent.generate_question(ctx(history=strong, asked_topics=["introduction"], asked_questions=["x"], number=2)).topic == "motivation"


def test_hr_uses_llm_question_when_valid():
    q = HRAgent("s", FakeLLM(), emb).generate_question(ctx())
    assert q.source == "llm" and q.text.startswith("Fake LLM question")


def test_llm_duplicate_rejected_falls_back():
    llm = FakeLLM()
    first = HRAgent("s", llm, emb).generate_question(ctx())
    again = HRAgent("s", DownLLM(), emb).generate_question(ctx(asked_questions=[first.text]))
    assert again.source == "fallback"


def test_technical_resume_personalisation():
    resume = {"projects": ["Pedestrian Crossing Intention Prediction using CNN and Bi-LSTM"], "skills": ["python"]}
    q = TechnicalAgent("s", DownLLM(), emb).generate_question(ctx(resume=resume, number=2, difficulty="MEDIUM"))
    assert q.resume_grounded and "Pedestrian Crossing" in q.text


def test_technical_role_specific_and_reinforce():
    agent = TechnicalAgent("s", DownLLM(), emb)
    q = agent.generate_question(ctx(difficulty="EASY", action="reinforce", asked_topics=["overfitting"], asked_questions=[]))
    assert q.difficulty == "EASY" and q.topic == "overfitting"


def test_extract_json_handles_fences_and_prose():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! {"a": 2} hope it helps') == {"a": 2}
    assert extract_json("no json here") is None


def test_ollama_unavailable_raises_cleanly():
    from services.ollama_service import LLMUnavailable
    svc = OllamaService("http://127.0.0.1:9", "x", timeout=1, retries=0)
    with pytest.raises(LLMUnavailable):
        svc.chat([{"role": "user", "content": "hi"}])


# ------------------------------------------------------------------ evaluator
def test_evaluator_heuristic_fallback_and_caps():
    ev = AnswerEvaluator(DownLLM(), emb)
    empty = ev.evaluate("technical", "What is overfitting?", "")
    assert empty["overall"] == 0
    short = ev.evaluate("hr", "Tell me about yourself", "I am a student.")
    assert short["method"] == "heuristic" and max(v for k, v in short.items() if k in ("clarity", "communication")) <= 3.0
    long = ev.evaluate("hr", "Tell me about yourself", "I am a final year computer science student. " * 8 + "For example, I built a project because I enjoy solving problems. As a result I learned a lot.")
    assert long["overall"] > short["overall"]


def test_evaluator_returns_structured_scores_with_llm():
    ev = AnswerEvaluator(FakeLLM(), emb).evaluate("technical", "Explain overfitting", "Overfitting happens when a model memorises training data, so regularisation and validation help. " * 3, "ai_ml_engineer")
    for k in ("clarity", "communication", "confidence", "completeness", "relevance", "technical_accuracy", "depth", "feedback", "improvement"):
        assert k in ev
    assert ev["method"] == "llm+heuristic" and 0 <= ev["overall"] <= 10


def test_star_detection_heuristic():
    ev = AnswerEvaluator(DownLLM(), emb)
    star = "When our team faced a deadline in my final project, my role was to build the API. I decided to split the work, I implemented the endpoints and as a result we delivered on time and improved speed by 30%. " * 2
    r = ev.evaluate("manager", "Tell me about a deadline", star)
    assert all(r[k] >= 4 for k in ("situation", "task", "action", "result"))
    assert ev.evaluate("manager", "Tell me about a deadline", "I am hardworking and like teamwork in general and always try hard every day.")["result"] < 4


def test_evaluator_survives_malformed_llm():
    class Bad(DownLLM):
        def generate_json(self, *a, **k):
            from services.ollama_service import LLMError
            raise LLMError("malformed")
    assert AnswerEvaluator(Bad(), emb).evaluate("hr", "q?", "I have several years of relevant experience because I enjoy it.")["method"] == "heuristic"


# ---------------------------------------------------------------- adaptive
STRONG = {"technical_accuracy": 9, "depth": 8, "concept_understanding": 9, "relevance": 9, "completeness": 8, "overall": 8.8}
WEAK = {"technical_accuracy": 2, "depth": 2, "concept_understanding": 3, "relevance": 6, "completeness": 3, "overall": 3}
AVG = {"technical_accuracy": 6, "depth": 6, "concept_understanding": 6, "relevance": 7, "completeness": 6, "overall": 6.2}


def test_adaptive_increase_maintain_reinforce():
    assert adaptive.decide("MEDIUM", "technical", STRONG).difficulty == "HARD"
    assert adaptive.decide("MEDIUM", "technical", AVG).action == "maintain"
    d = adaptive.decide("MEDIUM", "technical", WEAK)
    assert d.difficulty == "EASY" and d.action == "reinforce"


def test_adaptive_bounds_and_history():
    assert adaptive.decide("HARD", "technical", STRONG).difficulty == "HARD"
    assert adaptive.decide("EASY", "technical", WEAK).difficulty == "EASY"
    # a single good answer after several weak ones must not jump up
    # relevance gate: a strong-looking but irrelevant answer must not raise difficulty
    assert adaptive.decide("MEDIUM", "technical", {**STRONG, "relevance": 2, "technical_accuracy": 8}).action != "increase"
    # substantive but off-topic and weak: stay at the same level rather than punishing difficulty
    off = {"technical_accuracy": 3, "depth": 3, "concept_understanding": 3, "relevance": 2, "completeness": 7, "overall": 3.5}
    assert adaptive.decide("MEDIUM", "technical", off).difficulty == "MEDIUM"
    # history matters: one strong answer after weak ones is smoothed (needs the blended signal >= 8)
    assert adaptive.decide("MEDIUM", "technical", {**STRONG, "technical_accuracy": 8.5, "depth": 7, "concept_understanding": 7.5, "completeness": 7}, [WEAK, WEAK, WEAK]).action != "increase"
