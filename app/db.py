"""Database access."""

import os

import psycopg
from psycopg.types.json import Jsonb

from app.schemas import Criterion, ScoringResult


def connect() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"])


def get_job(conn: psycopg.Connection, job_slug: str) -> tuple[int, str] | None:
    return conn.execute("SELECT id, title FROM jobs WHERE slug = %s", (job_slug,)).fetchone()


def insert_application(conn: psycopg.Connection, job_id: int, cv_sha256: str) -> str:
    row = conn.execute(
        "INSERT INTO applications (job_id, cv_sha256) VALUES (%s, %s) RETURNING id",
        (job_id, cv_sha256),
    ).fetchone()
    return str(row[0])


def insert_evaluation(
    conn: psycopg.Connection,
    application_id: str,
    criteria: list[Criterion],
    result: ScoringResult,
) -> str:
    ev = result.evaluation
    row = conn.execute(
        """
        INSERT INTO evaluations
            (application_id, status, model, prompt_version, attempts, criteria,
             score, recommendation, result, error)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            application_id,
            result.status.value,
            result.model,
            result.prompt_version,
            result.attempts,
            Jsonb([c.model_dump() for c in criteria]),
            ev.score if ev else None,
            ev.recommendation.value if ev else None,
            Jsonb(ev.model_dump(mode="json")) if ev else None,
            result.error,
        ),
    ).fetchone()
    return str(row[0])
