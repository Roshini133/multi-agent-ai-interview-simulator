from tests.conftest import register


def test_health(client):
    assert client.get("/api/health").json["data"]["status"] == "ok"


def test_requires_auth(client):
    r = client.post("/api/interview/start", json={"role": "java_developer"})
    assert r.status_code == 401 and r.json["success"] is False


def test_session_creation(client, auth):
    r = client.post("/api/interview/start", json={"role": "java_developer"}, headers=auth)
    assert r.status_code == 201
    d = r.json["data"]
    assert len(d["session_id"]) == 36 and d["status"] == "created" and d["total_questions"] == 12


def test_invalid_role(client, auth):
    assert client.post("/api/interview/start", json={"role": "astronaut"}, headers=auth).json["error"]["code"] == "invalid_role"


def test_invalid_session_id(client, auth):
    r = client.post("/api/interview/question", json={"session_id": "does-not-exist"}, headers=auth)
    assert r.status_code == 404 and r.json["error"]["code"] == "invalid_session"


def test_session_isolation_between_users(client, session_id):
    other = register(client, "b@example.com", "Bob Other")
    r = client.get(f"/api/interview/{session_id}", headers=other)
    assert r.status_code == 403


def test_unique_agents_per_session(app, client, auth):
    a = client.post("/api/interview/start", json={"role": "java_developer"}, headers=auth).json["data"]["session_id"]
    b = client.post("/api/interview/start", json={"role": "java_developer"}, headers=auth).json["data"]["session_id"]
    sm = app.extensions["services"].sessions
    assert sm.panel_for(a).hr is not sm.panel_for(b).hr
    assert sm.panel_for(a).technical is not sm.panel_for(b).technical


def test_no_stack_trace_on_bad_json(client, auth):
    r = client.post("/api/interview/start", data="not json", headers={**auth, "Content-Type": "application/json"})
    assert r.status_code == 400 and "Traceback" not in r.get_data(as_text=True)
