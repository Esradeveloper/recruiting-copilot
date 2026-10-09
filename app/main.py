"""FastAPI service: receives a CV PDF and returns an AI recommendation."""

import logging
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

load_dotenv()

from app import db  # noqa: E402
from app.pdf_text import PdfTextError, extract_text  # noqa: E402
from app.schemas import ScoringResult  # noqa: E402
from app.scoring import score_cv  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("app")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024

app = FastAPI(title="Recruiting Copilot")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/evaluate", response_model=ScoringResult)
async def evaluate(job_slug: str = Form(...), cv: UploadFile = ...) -> ScoringResult:
    request_id = uuid.uuid4()
    pdf_bytes = await cv.read(MAX_UPLOAD_BYTES + 1)
    if len(pdf_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "CV larger than 5 MB")

    try:
        cv_text = extract_text(pdf_bytes)
    except PdfTextError as e:
        raise HTTPException(422, str(e)) from e

    with db.connect() as conn:
        job = db.get_job_with_criteria(conn, job_slug)
    if job is None:
        raise HTTPException(404, f"unknown job: {job_slug}")
    title, criteria = job

    # Log IDs and metadata only, never CV content.
    log.info("evaluate request=%s job=%s cv_chars=%d", request_id, job_slug, len(cv_text))
    result = await run_in_threadpool(score_cv, title, criteria, cv_text)
    log.info("evaluate request=%s status=%s attempts=%d", request_id, result.status.value, result.attempts)
    return result
