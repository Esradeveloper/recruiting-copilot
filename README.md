# Recruiting Copilot

AI-assisted CV screening workflow: an application arrives via n8n webhook, a Python service scores the CV against job-specific criteria with Claude, every evaluation is stored in an audit log, and a human makes the final decision in Slack.

> The AI only gives a recommendation with reasoning. It never rejects anyone automatically (EU AI Act: recruiting is a high-risk use case).

All data in this repository is fictional.

## Status
Work in progress.
- Day 1: repository, Docker, PostgreSQL schema, fictional test data
- Day 2: PDF text extraction, Claude scoring with schema-validated JSON and one retry

## Quick start
```bash
cp .env.example .env          # fill in values
docker compose up -d          # PostgreSQL 16 + pgvector, schema and seed load on first start
docker compose exec db psql -U copilot -d recruiting -c "SELECT slug, title FROM jobs;"
```

Run the API locally (Python 3.12):
```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload
curl -X POST localhost:8000/evaluate \
  -F job_slug=ai-automation-engineer -F cv=@data/cvs/cv_01_strong_ai.pdf
```

Run the tests (no API calls, Claude is faked):
```bash
.venv/bin/python -m pytest
```

Regenerate the fictional CV PDFs: `.venv/bin/python scripts/make_test_cvs.py`

## How scoring works
1. `pypdf` extracts the CV text (no OCR; scanned PDFs are rejected).
2. Claude scores each job criterion 0-100 with evidence from the CV, plus strengths, gaps, a recommendation and reasoning. The output is constrained to a JSON schema and validated with Pydantic.
3. Code checks what the schema cannot: every criterion scored exactly once. On any invalid answer the request is retried once with the error message; after that the result is returned as `invalid_output`.
4. The overall `score` is the weighted average of the criterion scores, computed in code so it is deterministic.
5. The CV is passed as untrusted data inside `<cv>` tags, and the prompt tells the model to ignore protected attributes. Logs contain request IDs and metadata only, never CV content.

## Data model
| Table | Purpose |
|---|---|
| `jobs`, `criteria` | Job postings and weighted scoring criteria |
| `applications` | Incoming application, CV referenced by SHA-256 only |
| `evaluations` | AI recommendation incl. model, prompt version, status, full JSON (append-only) |
| `decisions` | Human decision from Slack, by Slack user ID (append-only) |
