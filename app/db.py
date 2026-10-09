"""Database access."""

import os

import psycopg

from app.schemas import Criterion


def connect() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"])


def get_job_with_criteria(conn: psycopg.Connection, job_slug: str) -> tuple[str, list[Criterion]] | None:
    row = conn.execute("SELECT id, title FROM jobs WHERE slug = %s", (job_slug,)).fetchone()
    if row is None:
        return None
    job_id, title = row
    rows = conn.execute(
        "SELECT name, description, weight FROM criteria WHERE job_id = %s ORDER BY id",
        (job_id,),
    ).fetchall()
    return title, [Criterion(name=n, description=d, weight=float(w)) for n, d, w in rows]
