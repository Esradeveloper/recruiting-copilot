"""Build n8n/recruiting_intake.json from n8n/build_slack_message.js.

Keeps the Code node source reviewable as a .js file. Run after editing the .js:
    python3 scripts/build_n8n_workflow.py
"""

import json
import uuid
from pathlib import Path

N8N_DIR = Path(__file__).resolve().parent.parent / "n8n"


def node(id_, name, type_, version, x, parameters, **extra):
    return {"id": id_, "name": name, "type": type_, "typeVersion": version,
            "position": [x, 0], "parameters": parameters, **extra}


def chain(*names):
    return {a: {"main": [[{"node": b, "type": "main", "index": 0}]]} for a, b in zip(names, names[1:])}


def main() -> None:
    code = (N8N_DIR / "build_slack_message.js").read_text()
    nodes = [
        node("a1", "Application webhook", "n8n-nodes-base.webhook", 2, 0,
             {"httpMethod": "POST", "path": "application", "responseMode": "responseNode",
              "options": {"binaryPropertyName": "cv"}},
             webhookId="7c2f0a52-3b1e-4f7e-9d61-0a1b2c3d4e5f"),
        node("a2", "Evaluate CV", "n8n-nodes-base.httpRequest", 4.2, 240,
             {"method": "POST", "url": "={{ $env.COPILOT_API_URL }}/evaluate",
              "sendHeaders": True, "headerParameters": {"parameters": [
                  {"name": "X-API-Key", "value": "={{ $env.COPILOT_API_KEY }}"}]},
              "sendBody": True, "contentType": "multipart-form-data",
              "bodyParameters": {"parameters": [
                  {"name": "job_slug", "value": "={{ $json.body.job_slug }}"},
                  {"parameterType": "formBinaryData", "name": "cv", "inputDataFieldName": "cv0"}]},
              "options": {"timeout": 120000, "response": {"response": {"neverError": True}}}},
             onError="continueRegularOutput"),
        node("a3", "Build Slack message", "n8n-nodes-base.code", 2, 480, {"jsCode": code}),
        node("a4", "Post to Slack", "n8n-nodes-base.httpRequest", 4.2, 720,
             {"method": "POST", "url": "https://slack.com/api/chat.postMessage",
              "sendHeaders": True, "headerParameters": {"parameters": [
                  {"name": "Authorization", "value": "=Bearer {{ $env.SLACK_BOT_TOKEN }}"}]},
              "sendBody": True, "specifyBody": "json",
              "jsonBody": "={{ JSON.stringify($json.slack) }}", "options": {}},
             onError="continueRegularOutput"),
        node("a5", "Respond", "n8n-nodes-base.respondToWebhook", 1.1, 960,
             {"respondWith": "json",
              "responseBody": "={{ JSON.stringify({ ...$('Build Slack message').first().json.response, "
                              "slack_ok: $json.ok === true, slack_error: $json.error || null }) }}",
              "options": {}}),
    ]
    workflow = {
        "id": "ZheycBW7owPtupFN",  # fixed so re-importing updates the same workflow
        "name": "Recruiting intake",
        "nodes": nodes,
        "connections": chain(*(n["name"] for n in nodes)),
        "settings": {"executionOrder": "v1"},
        "pinData": {},
        "active": False,
    }
    # n8n needs a versionId to update an existing workflow; derive it from the
    # content so the file only changes when the workflow does.
    content = json.dumps(workflow, sort_keys=True)
    workflow["versionId"] = str(uuid.uuid5(uuid.NAMESPACE_URL, content))
    out = N8N_DIR / "recruiting_intake.json"
    out.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {out.name}")


if __name__ == "__main__":
    main()
