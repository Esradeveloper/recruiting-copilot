"""FastAPI service: receives a CV PDF and returns an AI recommendation."""

import hashlib
import hmac
import logging
import os
import uuid
from urllib.parse import parse_qs

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, Form, Header, HTTPException, Request, Response, UploadFile
from starlette.concurrency import run_in_threadpool

load_dotenv()

from app import db, slack  # noqa: E402
from app.pdf_text import PdfTextError, extract_text  # noqa: E402
from app.rag import MIN_CRITERIA, retrieve_criteria  # noqa: E402
from app.schemas import EvaluateResponse  # noqa: E402
from app.scoring import score_cv  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("app")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024

app = FastAPI(title="Recruiting Copilot")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def require_api_key(x_api_key: str = Header(default="")) -> None:
    """/evaluate spends API credits, so only callers with the shared key (n8n) may use it."""
    expected = os.environ.get("COPILOT_API_KEY")
    if not expected:
        raise HTTPException(503, "COPILOT_API_KEY not configured")
    if not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(401, "invalid API key")


@app.post("/evaluate", response_model=EvaluateResponse, dependencies=[Depends(require_api_key)])
async def evaluate(job_slug: str = Form(...), cv: UploadFile = ...) -> EvaluateResponse:
    pdf_bytes = await cv.read(MAX_UPLOAD_BYTES + 1)
    if len(pdf_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "CV larger than 5 MB")

    try:
        cv_text = extract_text(pdf_bytes)
    except PdfTextError as e:
        raise HTTPException(422, str(e)) from e

    with db.connect() as conn:
        job = db.get_job(conn, job_slug)
        if job is None:
            raise HTTPException(404, f"unknown job: {job_slug}")
        job_id, title = job
        criteria = retrieve_criteria(conn, job_id)
        if len(criteria) < MIN_CRITERIA:
            raise HTTPException(422, f"only {len(criteria)} matching criteria for job {job_slug}")
        application_id = db.insert_application(conn, job_id, hashlib.sha256(pdf_bytes).hexdigest())

    # Log IDs and metadata only, never CV content.
    log.info("evaluate application=%s job=%s criteria=%d cv_chars=%d",
             application_id, job_slug, len(criteria), len(cv_text))
    result = await run_in_threadpool(score_cv, title, criteria, cv_text)

    # Every outcome is stored, including invalid output and API errors.
    with db.connect() as conn:
        evaluation_id = db.insert_evaluation(conn, application_id, criteria, result)
    log.info("evaluate application=%s evaluation=%s status=%s attempts=%d",
             application_id, evaluation_id, result.status.value, result.attempts)

    return EvaluateResponse(
        **result.model_dump(),
        application_id=application_id,
        evaluation_id=evaluation_id,
        job_title=title,
        criteria=criteria,
    )


def post_to_slack(response_url: str, message: dict) -> None:
    try:
        httpx.post(response_url, json=message, timeout=10).raise_for_status()
    except httpx.HTTPError as e:
        log.error("slack response_url update failed: %s", type(e).__name__)


@app.post("/slack/interactions")
async def slack_interactions(request: Request, background: BackgroundTasks) -> Response:
    """Receives button clicks from Slack and stores the human decision."""
    signing_secret = os.environ.get("SLACK_SIGNING_SECRET")
    if not signing_secret:
        raise HTTPException(503, "SLACK_SIGNING_SECRET not configured")

    body = await request.body()
    try:
        slack.verify_signature(
            signing_secret,
            request.headers.get("X-Slack-Request-Timestamp", ""),
            body,
            request.headers.get("X-Slack-Signature", ""),
        )
    except slack.SlackRequestError as e:
        log.warning("rejected slack request: %s", e)
        raise HTTPException(401, "invalid slack signature") from e

    try:
        click = slack.parse_button_click(parse_qs(body.decode())["payload"][0])
        uuid.UUID(click.evaluation_id)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, "unsupported slack payload") from e

    try:
        with db.connect() as conn:
            decision, created = db.insert_decision(conn, click.evaluation_id, click.decision, click.user_id)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e

    log.info("decision evaluation=%s decision=%s by=%s created=%s",
             click.evaluation_id, decision, click.user_id, created)
    if created:
        message = slack.decided_message(click.blocks, decision, click.user_id)
    else:
        message = {"response_type": "ephemeral", "replace_original": False,
                   "text": f"Hier wurde bereits entschieden: {decision}"}
    # Slack expects an answer within 3 seconds; update the message afterwards.
    # The ack itself must have an empty body - a JSON body like "{}" makes Slack
    # try to parse it as a message payload and show a "could not process" warning.
    background.add_task(post_to_slack, click.response_url, message)
    return Response(status_code=200)
