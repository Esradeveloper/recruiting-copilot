"""Compute embeddings for jobs and criteria that do not have one yet.

Run after the database is created or new rows are added:
    .venv/bin/python scripts/backfill_embeddings.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402
from pgvector.psycopg import register_vector  # noqa: E402

from app import db  # noqa: E402
from app.rag import embed  # noqa: E402


def backfill(conn, table: str, text_sql: str) -> int:
    rows = conn.execute(f"SELECT id, {text_sql} FROM {table} WHERE embedding IS NULL").fetchall()
    if not rows:
        return 0
    vectors = embed([text for _, text in rows])
    for (row_id, _), vec in zip(rows, vectors):
        conn.execute(f"UPDATE {table} SET embedding = %s WHERE id = %s", (vec, row_id))
    return len(rows)


def main() -> None:
    load_dotenv()
    with db.connect() as conn:
        register_vector(conn)
        n_jobs = backfill(conn, "jobs", "title || '. ' || description")
        n_criteria = backfill(conn, "criteria", "description")
    print(f"embedded {n_jobs} jobs, {n_criteria} criteria")


if __name__ == "__main__":
    main()
