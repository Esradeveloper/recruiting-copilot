"""Pydantic models for criteria, Claude's assessment and the API response."""

from enum import Enum

from pydantic import BaseModel, Field


class Recommendation(str, Enum):
    advance = "advance"
    review = "review"
    reject_suggested = "reject_suggested"


class Criterion(BaseModel):
    name: str
    description: str
    weight: float = Field(gt=0, le=1)
    similarity: float | None = None  # set when retrieved via RAG


class CriterionScore(BaseModel):
    criterion: str = Field(description="Exact criterion name from the list provided.")
    score: int = Field(ge=0, le=100, description="0 = no evidence, 100 = fully met.")
    evidence: str = Field(description="Short quote or paraphrase from the CV supporting the score.")


class Assessment(BaseModel):
    """What Claude must return. The overall score is computed in code, not by the model."""

    criteria_scores: list[CriterionScore]
    strengths: list[str]
    gaps: list[str]
    recommendation: Recommendation
    reasoning: str = Field(description="2-4 sentences explaining the recommendation.")


class Evaluation(Assessment):
    score: int = Field(ge=0, le=100, description="Weighted average of criteria scores.")


class EvaluationStatus(str, Enum):
    ok = "ok"
    invalid_output = "invalid_output"
    error = "error"


class ScoringResult(BaseModel):
    status: EvaluationStatus
    model: str
    prompt_version: str
    attempts: int
    evaluation: Evaluation | None = None
    error: str | None = None
    input_tokens: int = 0   # summed over all attempts, for cost tracking
    output_tokens: int = 0


class EvaluateResponse(ScoringResult):
    application_id: str
    job_title: str
    evaluation_id: str
    criteria: list[Criterion]
