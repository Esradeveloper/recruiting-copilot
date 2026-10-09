"""Retrieve the scoring criteria relevant to a job via pgvector similarity search."""

from functools import lru_cache

import numpy as np
import psycopg
from fastembed import TextEmbedding

from app.schemas import Criterion

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"  # 384 dimensions, must match db/01_schema.sql
TOP_K = 7
MIN_SIMILARITY = 0.60  # tuned on the seed jobs, see notizen.md (Tag 3)
MIN_CRITERIA = 3


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    return TextEmbedding(EMBEDDING_MODEL)


def embed(texts: list[str]) -> list[np.ndarray]:
    return list(_model().embed(texts))


def retrieve_criteria(
    conn: psycopg.Connection,
    job_id: int,
    top_k: int = TOP_K,
    min_similarity: float = MIN_SIMILARITY,
) -> list[Criterion]:
    """Return the criteria closest to the job description, best match first."""
    rows = conn.execute(
        """
        SELECT c.name, c.description, c.weight, 1 - (c.embedding <=> j.embedding) AS similarity
        FROM criteria c, jobs j
        WHERE j.id = %s AND c.embedding IS NOT NULL AND j.embedding IS NOT NULL
        ORDER BY c.embedding <=> j.embedding
        LIMIT %s
        """,
        (job_id, top_k),
    ).fetchall()
    return [
        Criterion(name=n, description=d, weight=float(w), similarity=round(float(s), 3))
        for n, d, w, s in rows
        if s >= min_similarity
    ]
