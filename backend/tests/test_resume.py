import io

from services.resume_parser import extract_text, parse_resume
from tests.conftest import RESUME_LINES, make_resume_pdf


def test_parse_resume(resume_pdf):
    p = parse_resume(extract_text(resume_pdf))
    assert p["name"] == "Asha Patel" and p["email"] == "asha.patel@example.com"
    assert {"python", "tensorflow", "opencv"} <= set(p["skills"])
    assert any("Bi-LSTM" in x for x in p["projects"])
    assert p["internships"] and p["certifications"] and p["education"] and p["achievements"]


def test_upload_resume_api(client, auth, session_id, resume_pdf):
    r = client.post("/api/resume/upload", headers=auth, data={"session_id": session_id, "file": (io.BytesIO(resume_pdf), "My Resume!!.pdf")}, content_type="multipart/form-data")
    assert r.status_code == 201 and r.json["data"]["parsed"]["name"] == "Asha Patel"
    assert client.get(f"/api/resume/{session_id}", headers=auth).status_code == 200


def test_upload_rejects_non_pdf(client, auth, session_id):
    r = client.post("/api/resume/upload", headers=auth, data={"session_id": session_id, "file": (io.BytesIO(b"hello world"), "resume.pdf")}, content_type="multipart/form-data")
    assert r.status_code == 400 and r.json["error"]["code"] == "invalid_file"
    r = client.post("/api/resume/upload", headers=auth, data={"session_id": session_id, "file": (io.BytesIO(b"%PDF-1.4"), "resume.txt")}, content_type="multipart/form-data")
    assert r.status_code == 400


def test_upload_corrupt_pdf_is_clean_error(client, auth, session_id):
    r = client.post("/api/resume/upload", headers=auth, data={"session_id": session_id, "file": (io.BytesIO(b"%PDF-1.4 garbage garbage"), "resume.pdf")}, content_type="multipart/form-data")
    assert r.status_code == 422 and "Traceback" not in r.get_data(as_text=True)


def test_upload_size_limit(client, auth, session_id, app):
    app.config["MAX_RESUME_MB"] = 1
    big = b"%PDF-1.4" + b"0" * (1024 * 1024 + 10)
    r = client.post("/api/resume/upload", headers=auth, data={"session_id": session_id, "file": (io.BytesIO(big), "resume.pdf")}, content_type="multipart/form-data")
    assert r.status_code == 413
