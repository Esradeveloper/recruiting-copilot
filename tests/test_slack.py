import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from app import main, slack

SECRET = "test-signing-secret"
EVAL_ID = "11111111-2222-3333-4444-555555555555"


def sign(body: bytes, ts: str, secret: str = SECRET) -> str:
    return "v0=" + hmac.new(secret.encode(), b"v0:" + ts.encode() + b":" + body, hashlib.sha256).hexdigest()


def click_payload(action_id="decision_advance", value=EVAL_ID) -> dict:
    return {
        "type": "block_actions",
        "user": {"id": "U123"},
        "response_url": "https://hooks.slack.test/response",
        "actions": [{"action_id": action_id, "value": value}],
        "message": {"blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": "Score 80"}},
            {"type": "actions", "elements": []},
        ]},
    }


def test_valid_signature_passes():
    ts = str(int(time.time()))
    slack.verify_signature(SECRET, ts, b"body", sign(b"body", ts))


@pytest.mark.parametrize("case", ["wrong_secret", "tampered_body", "too_old", "no_timestamp"])
def test_invalid_requests_rejected(case):
    ts = str(int(time.time()))
    body, sig = b"body", sign(b"body", ts)
    if case == "wrong_secret":
        sig = sign(body, ts, "other")
    elif case == "tampered_body":
        body = b"body2"
    elif case == "too_old":
        ts = str(int(time.time()) - 600)
        sig = sign(body, ts)
    elif case == "no_timestamp":
        ts = ""
    with pytest.raises(slack.SlackRequestError):
        slack.verify_signature(SECRET, ts, body, sig)


def test_parse_click_maps_action_to_decision():
    click = slack.parse_button_click(json.dumps(click_payload("decision_reject")))
    assert (click.decision, click.user_id, click.evaluation_id) == ("reject", "U123", EVAL_ID)


def test_unknown_action_rejected():
    with pytest.raises(slack.SlackRequestError):
        slack.parse_button_click(json.dumps(click_payload("delete_everything")))


def test_decided_message_removes_buttons():
    msg = slack.decided_message(click_payload()["message"]["blocks"], "advance", "U123")
    types = [b["type"] for b in msg["blocks"]]
    assert "actions" not in types
    assert "<@U123>" in msg["blocks"][-1]["elements"][0]["text"]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SLACK_SIGNING_SECRET", SECRET)
    stored, posted = [], []

    class FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_insert(conn, evaluation_id, decision, user_id):
        created = not stored
        stored.append((evaluation_id, decision, user_id))
        return (stored[0][1], created)

    monkeypatch.setattr(main.db, "connect", lambda: FakeConn())
    monkeypatch.setattr(main.db, "insert_decision", fake_insert)
    monkeypatch.setattr(main, "post_to_slack", lambda url, msg: posted.append(msg))
    return TestClient(main.app), stored, posted


def send(tc, payload, secret=SECRET):
    body = urlencode({"payload": json.dumps(payload)}).encode()
    ts = str(int(time.time()))
    return tc.post("/slack/interactions", content=body, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Slack-Request-Timestamp": ts,
        "X-Slack-Signature": sign(body, ts, secret),
    })


def test_endpoint_stores_decision_and_updates_message(client):
    tc, stored, posted = client
    assert send(tc, click_payload()).status_code == 200
    assert stored == [(EVAL_ID, "advance", "U123")]
    assert posted[0]["replace_original"] is True


def test_second_click_does_not_override(client):
    tc, stored, posted = client
    send(tc, click_payload("decision_advance"))
    send(tc, click_payload("decision_reject"))
    assert posted[1]["response_type"] == "ephemeral"
    assert "advance" in posted[1]["text"]


def test_endpoint_rejects_forged_request(client):
    tc, stored, _ = client
    assert send(tc, click_payload(), secret="attacker").status_code == 401
    assert stored == []
