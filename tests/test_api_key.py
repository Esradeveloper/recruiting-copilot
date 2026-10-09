from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)


def post(headers=None):
    return client.post("/evaluate", data={"job_slug": "x"}, files={"cv": ("cv.pdf", b"%PDF")}, headers=headers or {})


def test_missing_key_rejected(monkeypatch):
    monkeypatch.setenv("COPILOT_API_KEY", "secret")
    assert post().status_code == 401


def test_wrong_key_rejected(monkeypatch):
    monkeypatch.setenv("COPILOT_API_KEY", "secret")
    assert post({"X-API-Key": "guess"}).status_code == 401


def test_unconfigured_key_fails_closed(monkeypatch):
    monkeypatch.delenv("COPILOT_API_KEY", raising=False)
    assert post({"X-API-Key": ""}).status_code == 503


def test_correct_key_passes_auth(monkeypatch):
    monkeypatch.setenv("COPILOT_API_KEY", "secret")
    # Auth passes; the fake PDF then fails text extraction with 422.
    assert post({"X-API-Key": "secret"}).status_code == 422
