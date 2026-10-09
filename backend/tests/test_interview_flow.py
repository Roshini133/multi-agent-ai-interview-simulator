import io

from services.report_service import build_pdf


def run_interview(client, auth, sid, answers, stop_after=None):
    n = 0
    while True:
        q = client.post("/api/interview/question", json={"session_id": sid}, headers=auth).json["data"]
        if q["finished"]:
            return n
        question = q["question"]
        text = answers[question["agent"]]
        r = client.post("/api/interview/answer", headers=auth, json={"session_id": sid, "question_id": question["id"], "answer": text, "input_mode": "voice", "duration_seconds": 40})
        assert r.status_code == 200, r.json
        n += 1
        if stop_after and n >= stop_after:
            return n


ANSWERS = {
    "hr": "I am a final year computer science student who enjoys building practical AI projects. For example, I built an interview simulator because I like solving real problems, and as a result I learned a lot about teamwork.",
    "technical": "Overfitting happens when a model memorises training data and fails to generalise. To reduce it I use regularisation, dropout, more data and cross validation, because validation loss reveals the gap. For example in my CNN project I used early stopping.",
    "manager": "When our team faced a tight deadline in my final year project, my role was to build the backend API. I decided to split tasks, I implemented the endpoints and I organised daily check-ins. As a result we delivered on time and improved response time by 30%.",
}


def test_full_interview_flow_with_report(client, auth, session_id, resume_pdf):
    client.post("/api/resume/upload", headers=auth, data={"session_id": session_id, "file": (io.BytesIO(resume_pdf), "r.pdf")}, content_type="multipart/form-data")
    q1 = client.post("/api/interview/question", json={"session_id": session_id}, headers=auth).json["data"]["question"]
    assert q1["agent"] == "hr" and q1["intro"] and q1["question_number"] == 1
    # idempotent: refreshing returns the same pending question
    assert client.post("/api/interview/question", json={"session_id": session_id}, headers=auth).json["data"]["question"]["id"] == q1["id"]
    # cannot answer a question twice / with empty text
    assert client.post("/api/interview/answer", headers=auth, json={"session_id": session_id, "question_id": q1["id"], "answer": ""}).status_code == 400

    assert run_interview(client, auth, session_id, ANSWERS) + 0 >= 0
    info = client.get(f"/api/interview/{session_id}", headers=auth).json["data"]
    assert info["questions_answered"] == 12 and info["status"] == "active"

    # progress dashboard before completion
    dash = client.get(f"/api/dashboard/{session_id}", headers=auth).json["data"]
    assert dash["scores"]["overall"] > 0 and len(dash["difficulty_progress"]) == 12

    r = client.post(f"/api/interview/{session_id}/complete", headers=auth)
    assert r.status_code == 200 and r.json["data"]["session"]["status"] == "completed"
    # idempotent
    assert client.post(f"/api/interview/{session_id}/complete", headers=auth).status_code == 200

    rep = client.get(f"/api/report/{session_id}", headers=auth).json["data"]
    assert set(rep["agent_reviews"]) == {"hr", "technical", "manager"} and rep["panel"]["final_assessment"]
    assert "practice" in rep["panel"]["disclaimer"].lower()
    assert rep["scores"]["categories"]["resume_relevance"] is not None
    assert any(q["resume_grounded"] for q in rep["questions"])  # personalised via resume
    pdf = client.get(f"/api/report/{session_id}/pdf", headers=auth)
    assert pdf.status_code == 200 and pdf.data.startswith(b"%PDF") and len(pdf.data) > 3000
    # cannot answer after completion
    assert client.post("/api/interview/question", json={"session_id": session_id}, headers=auth).status_code == 409


def test_agent_order_and_difficulty_adaptation(client, auth, session_id):
    seen = []
    for _ in range(12):
        q = client.post("/api/interview/question", json={"session_id": session_id}, headers=auth).json["data"]["question"]
        seen.append(q["agent"])
        good = client.post("/api/interview/answer", headers=auth, json={"session_id": session_id, "question_id": q["id"], "answer": "ok"}).json["data"]
        assert good["adaptation"]["action"] in ("reinforce", "maintain", "increase")
    assert seen == ["hr"] * 4 + ["technical"] * 5 + ["manager"] * 3
    dash = client.get(f"/api/dashboard/{session_id}", headers=auth).json["data"]
    tech = [d for d in dash["difficulty_progress"] if d["agent"] == "technical"]
    assert tech[-1]["to"] == "EASY"  # weak answers lowered difficulty


def test_early_completion_and_not_started(client, auth, session_id):
    assert client.post(f"/api/interview/{session_id}/complete", headers=auth).status_code == 409
    run_interview(client, auth, session_id, ANSWERS, stop_after=3)
    r = client.post(f"/api/interview/{session_id}/complete", headers=auth)
    assert r.status_code == 200
    rep = client.get(f"/api/report/{session_id}", headers=auth).json["data"]
    assert rep["questions_answered"] == 3 and rep["agent_reviews"]["technical"]["score"] is None
    assert build_pdf(rep).startswith(b"%PDF")


def test_report_not_ready(client, auth, session_id):
    assert client.get(f"/api/report/{session_id}", headers=auth).json["error"]["code"] == "report_not_ready"


def test_skip_and_evaluate_endpoint(client, auth, session_id):
    q = client.post("/api/interview/question", json={"session_id": session_id}, headers=auth).json["data"]["question"]
    r = client.post("/api/interview/answer", headers=auth, json={"session_id": session_id, "question_id": q["id"], "skipped": True})
    assert r.status_code == 200 and r.json["data"]["evaluation"]["overall"] == 0
    ev = client.post("/api/interview/evaluate", headers=auth, json={"session_id": session_id, "question_id": q["id"]})
    assert ev.status_code == 200 and ev.json["data"]["overall"] == 0
    nxt = client.post("/api/interview/next", headers=auth, json={"session_id": session_id}).json["data"]
    assert nxt["question"]["index"] == 2


def test_llm_path_end_to_end(app, client, auth, session_id):
    from tests.conftest import FakeLLM
    llm = FakeLLM()
    svc = app.extensions["services"]
    svc.llm = svc.sessions.llm = svc.orchestrator.evaluator.llm = llm
    svc.sessions.release(session_id)  # agents are rebuilt lazily with the new LLM
    run_interview(client, auth, session_id, ANSWERS)
    client.post(f"/api/interview/{session_id}/complete", headers=auth)
    rep = client.get(f"/api/report/{session_id}", headers=auth).json["data"]
    assert rep["panel"]["source"] == "llm" and rep["questions"][0]["source"] == "llm" and rep["questions"][0]["method"] == "llm+heuristic"
