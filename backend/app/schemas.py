"""Shapes of the JSON the API sends and receives (validated by Pydantic)."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

Status = Literal["saved", "applied", "interview", "offer", "rejected"]


class ProfileIn(BaseModel):
    name: str = ""
    cv_text: str


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    cv_text: str
    chunk_count: int = 0


class AnalyzeIn(BaseModel):
    job_url: str = ""
    job_text: str = ""

    @model_validator(mode="after")
    def need_url_or_text(self):
        if not self.job_url.strip() and not self.job_text.strip():
            raise ValueError("Give a job link or paste the job text.")
        return self


class Match(BaseModel):
    skill: str
    importance: Literal["must", "nice"]
    matched: bool
    note: str
    evidence: list[str] = []
    similarity: float = 0.0


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company: str
    role: str
    job_url: str
    job_text: str
    status: Status
    match_score: float
    matches: list[Match]
    tailored_cv: str
    cover_letter: str
    notes: str
    created_at: datetime
    updated_at: datetime


class ApplicationUpdate(BaseModel):
    """Every field is optional: send only what you want to change."""

    company: str | None = None
    role: str | None = None
    status: Status | None = None
    tailored_cv: str | None = None
    cover_letter: str | None = None
    notes: str | None = None
