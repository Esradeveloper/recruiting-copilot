"""Slack interactivity: verify requests and turn button clicks into decisions."""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass

MAX_REQUEST_AGE_SECONDS = 300

# action_id of the buttons in the Slack message -> human_decision enum in the DB
ACTIONS = {"decision_advance": "advance", "decision_reject": "reject"}
LABELS = {"advance": ":white_check_mark: Weiter", "reject": ":x: Absage"}


class SlackRequestError(ValueError):
    pass


def verify_signature(signing_secret: str, timestamp: str, body: bytes, signature: str, now: float | None = None) -> None:
    """Raise unless the request was signed by Slack in the last 5 minutes."""
    try:
        ts = int(timestamp)
    except (TypeError, ValueError) as e:
        raise SlackRequestError("missing or invalid timestamp") from e
    if abs((now or time.time()) - ts) > MAX_REQUEST_AGE_SECONDS:
        raise SlackRequestError("request too old")

    base = b"v0:" + timestamp.encode() + b":" + body
    expected = "v0=" + hmac.new(signing_secret.encode(), base, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature or ""):
        raise SlackRequestError("invalid signature")


@dataclass
class ButtonClick:
    evaluation_id: str
    decision: str
    user_id: str
    response_url: str
    blocks: list[dict]


def parse_button_click(payload_json: str) -> ButtonClick:
    payload = json.loads(payload_json)
    if payload.get("type") != "block_actions" or not payload.get("actions"):
        raise SlackRequestError("not a button click")
    action = payload["actions"][0]
    if action.get("action_id") not in ACTIONS:
        raise SlackRequestError(f"unknown action: {action.get('action_id')}")
    return ButtonClick(
        evaluation_id=action["value"],
        decision=ACTIONS[action["action_id"]],
        user_id=payload["user"]["id"],
        response_url=payload["response_url"],
        blocks=payload.get("message", {}).get("blocks", []),
    )


def decided_message(blocks: list[dict], decision: str, user_id: str) -> dict:
    """Original message without buttons, plus who decided what."""
    kept = [b for b in blocks if b.get("type") != "actions"]
    kept.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"{LABELS[decision]} – entschieden von <@{user_id}>"}],
    })
    return {"replace_original": True, "text": f"Entscheidung: {decision}", "blocks": kept}
