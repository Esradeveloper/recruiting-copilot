"""Integration tests against the local PostgreSQL (docker compose up -d).

Each test runs in a transaction that is rolled back, so nothing is persisted.
Skipped when the database is not reachable.
"""

import os

import psycopg
import pytest
from dotenv import load_dotenv

from app import db
from app.rag import retrieve_criteria
from app.schemas import Evaluation, EvaluationStatus, ScoringResult

load_dotenv()


@pytest.fixture
def conn():
    try:
        connection = psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=2)
    except (KeyError, psycopg.OperationalError):
        pytest.skip("database not available")
    if connection.execute("SELECT count(*) FROM criteria WHERE embedding IS NULL").fetchone()[0]:
        pytest.skip("embeddings missing, run scripts/backfill_embeddings.py")
    yield connection
    connection.rollback()
    connection.close()


def job_id(conn, slug: str) -> int:
    return db.get_job(conn, slug)[0]


@pytest.mark.parametrize(
    "slug, must_include",
    [
        ("ai-automation-engineer", {"python", "llm_integration", "workflow_automation"}),
        ("backend-engineer", {"python", "api_design", "sql_data"}),
        ("recruiting-coordinator", {"interview_coordination", "candidate_communication", "ats_tools"}),
    ],
)
def test_retrieves_core_criteria(conn, slug, must_include):
    names = {c.name for c in retrieve_criteria(conn, job_id(conn, slug))}
    assert must_include <= names


def test_recruiting_job_gets_no_engineering_criteria(conn):
    names = {c.name for c in retrieve_criteria(conn, job_id(conn, "recruiting-coordinator"))}
    assert not names & {"python", "api_design", "llm_integration"}


def test_stores_ok_and_failed_evaluations(conn):
    jid = job_id(conn, "backend-engineer")
    criteria = retrieve_criteria(conn, jid)
    app_id = db.insert_application(conn, jid, "a" * 64)

    evaluation = Evaluation(
        criteria_scores=[{"criterion": c.name, "score": 50, "evidence": "-"} for c in criteria],
        strengths=[], gaps=[], recommendation="review", reasoning="r", score=50,
    )
    ok = ScoringResult(status=EvaluationStatus.ok, model="m", prompt_version="v1", attempts=1, evaluation=evaluation)
    failed = ScoringResult(status=EvaluationStatus.invalid_output, model="m", prompt_version="v1", attempts=2, error="bad")
    db.insert_evaluation(conn, app_id, criteria, ok)
    db.insert_evaluation(conn, app_id, criteria, failed)

    rows = conn.execute(
        "SELECT status, score, recommendation, error FROM evaluations WHERE application_id = %s ORDER BY status",
        (app_id,),
    ).fetchall()
    assert rows == [("ok", 50, "review", None), ("invalid_output", None, None, "bad")]


def test_evaluations_are_append_only(conn):
    jid = job_id(conn, "backend-engineer")
    app_id = db.insert_application(conn, jid, "b" * 64)
    failed = ScoringResult(status=EvaluationStatus.error, model="m", prompt_version="v1", attempts=1, error="x")
    db.insert_evaluation(conn, app_id, [], failed)
    with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
        conn.execute("UPDATE evaluations SET error = 'changed' WHERE application_id = %s", (app_id,))


def test_first_decision_wins(conn):
    jid = job_id(conn, "backend-engineer")
    app_id = db.insert_application(conn, jid, "c" * 64)
    failed = ScoringResult(status=EvaluationStatus.error, model="m", prompt_version="v1", attempts=1, error="x")
    eval_id = db.insert_evaluation(conn, app_id, [], failed)

    assert db.insert_decision(conn, eval_id, "advance", "U1") == ("advance", True)
    assert db.insert_decision(conn, eval_id, "reject", "U2") == ("advance", False)
    assert conn.execute("SELECT count(*) FROM decisions WHERE application_id = %s", (app_id,)).fetchone()[0] == 1


def test_decision_for_unknown_evaluation(conn):
    with pytest.raises(LookupError):
        db.insert_decision(conn, "00000000-0000-0000-0000-000000000000", "advance", "U1")
