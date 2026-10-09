from types import SimpleNamespace

import pytest
from pydantic import TypeAdapter, ValidationError

from app.schemas import Assessment, Criterion, EvaluationStatus
from app.scoring import MAX_ATTEMPTS, check_assessment, InvalidAssessment, score_cv, weighted_score

CRITERIA = [
    Criterion(name="python", description="Python", weight=0.75),
    Criterion(name="sql", description="SQL", weight=0.25),
]


def assessment(scores: dict[str, int]) -> Assessment:
    return Assessment(
        criteria_scores=[{"criterion": k, "score": v, "evidence": "..."} for k, v in scores.items()],
        strengths=["s"],
        gaps=["g"],
        recommendation="review",
        reasoning="r",
    )


def ok_response(a: Assessment):
    return SimpleNamespace(stop_reason="end_turn", parsed_output=a, model="claude-test")


def schema_error() -> ValidationError:
    try:
        TypeAdapter(Assessment).validate_json('{"criteria_scores": "nope"}')
    except ValidationError as e:
        return e
    raise AssertionError("expected ValidationError")


class FakeClient:
    """Returns (or raises) the queued responses in order and records each call."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = []
        self.messages = self

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def run(client):
    return score_cv("Engineer", CRITERIA, "cv text", client=client, model="claude-test")


def test_weighted_score():
    assert weighted_score(assessment({"python": 80, "sql": 40}), CRITERIA) == 70


def test_valid_first_try():
    client = FakeClient(ok_response(assessment({"python": 100, "sql": 0})))
    result = run(client)
    assert result.status == EvaluationStatus.ok
    assert result.attempts == 1
    assert result.evaluation.score == 75
    assert result.model == "claude-test"


def test_retries_once_after_schema_error():
    client = FakeClient(schema_error(), ok_response(assessment({"python": 50, "sql": 50})))
    result = run(client)
    assert result.status == EvaluationStatus.ok
    assert result.attempts == 2
    assert "previous answer was invalid" in client.calls[1]["messages"][0]["content"]


def test_retries_once_after_missing_criterion():
    client = FakeClient(
        ok_response(assessment({"python": 50})),
        ok_response(assessment({"python": 50, "sql": 50})),
    )
    assert run(client).status == EvaluationStatus.ok


def test_gives_up_after_two_invalid_answers():
    client = FakeClient(schema_error(), ok_response(assessment({"python": 1})))
    result = run(client)
    assert result.status == EvaluationStatus.invalid_output
    assert result.attempts == MAX_ATTEMPTS
    assert result.evaluation is None
    assert "missing=['sql']" in result.error
    assert len(client.calls) == MAX_ATTEMPTS


def test_refusal_counts_as_invalid():
    refusal = SimpleNamespace(stop_reason="refusal", parsed_output=None, model="claude-test")
    client = FakeClient(refusal, refusal)
    assert run(client).status == EvaluationStatus.invalid_output


def test_duplicate_criteria_rejected():
    a = assessment({"python": 1, "sql": 1})
    a.criteria_scores.append(a.criteria_scores[0])
    with pytest.raises(InvalidAssessment, match="duplicate"):
        check_assessment(a, CRITERIA)


def test_cv_text_is_wrapped_as_data():
    client = FakeClient(ok_response(assessment({"python": 1, "sql": 1})))
    run(client)
    content = client.calls[0]["messages"][0]["content"]
    assert "<cv>\ncv text\n</cv>" in content
    assert "untrusted" in client.calls[0]["system"]
