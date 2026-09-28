"""Database tables.

- Profile: your base CV (one per user; this first version has a single user).
- CvChunk: the CV split into small pieces, each with an embedding vector,
  so we can search "which part of my CV proves this skill?" with pgvector.
- Application: one job you are applying to, with the AI results and its status.
"""
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .config import settings
from .db import Base

STATUSES = ("saved", "applied", "interview", "offer", "rejected")


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    cv_text: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    chunks: Mapped[list["CvChunk"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class CvChunk(Base):
    __tablename__ = "cv_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim))

    profile: Mapped[Profile] = relationship(back_populates="chunks")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company: Mapped[str] = mapped_column(String(200), default="")
    role: Mapped[str] = mapped_column(String(200), default="")
    job_url: Mapped[str] = mapped_column(String(1000), default="")
    job_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="saved")
    match_score: Mapped[float] = mapped_column(Float, default=0.0)
    # List of {requirement, importance, matched, similarity, evidence}
    matches: Mapped[list] = mapped_column(JSON, default=list)
    tailored_cv: Mapped[str] = mapped_column(Text, default="")
    cover_letter: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
