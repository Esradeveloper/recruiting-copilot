"""FastAPI service: receives a CV PDF and returns an AI recommendation."""

import hashlib
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

load_dotenv()

from app import db  # noqa: E402
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


@app.post("/evaluate", response_model=EvaluateResponse)
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
        criteria=criteria,
    )
