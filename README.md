# Recruiting Copilot

AI-assisted CV screening workflow: an application arrives via n8n webhook, a Python service scores the CV against job-specific criteria with Claude, every evaluation is stored in an audit log, and a human makes the final decision in Slack.

> The AI only gives a recommendation with reasoning. It never rejects anyone automatically (EU AI Act: recruiting is a high-risk use case).

All data in this repository is fictional.

## Status
Work in progress. Day 1: repository, Docker, PostgreSQL schema, fictional test data.

## Quick start
```bash
cp .env.example .env          # fill in values
docker compose up -d          # PostgreSQL 16 + pgvector, schema and seed load on first start
docker compose exec db psql -U copilot -d recruiting -c "SELECT slug, title FROM jobs;"
```

Regenerate the fictional CV PDFs:
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python scripts/make_test_cvs.py
```

## Data model
| Table | Purpose |
|---|---|
| `jobs`, `criteria` | Job postings and weighted scoring criteria |
| `applications` | Incoming application, CV referenced by SHA-256 only |
| `evaluations` | AI recommendation incl. model, prompt version, status, full JSON (append-only) |
| `decisions` | Human decision from Slack, by Slack user ID (append-only) |
