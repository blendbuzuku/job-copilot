"""Save the CV and search it with pgvector."""
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .cv_parser import chunk_cv
from .embeddings import embed
from .models import CvChunk, Profile

PROFILE_ID = 1  # single-user for now


def get_profile(db: Session) -> Profile:
    profile = db.get(Profile, PROFILE_ID)
    if profile is None:
        profile = Profile(id=PROFILE_ID)
        db.add(profile)
        db.commit()
    return profile


def save_cv(db: Session, cv_text: str, name: str | None = None) -> Profile:
    """Store the CV and rebuild its searchable chunks."""
    profile = get_profile(db)
    profile.cv_text = cv_text
    if name is not None:
        profile.name = name

    db.execute(delete(CvChunk).where(CvChunk.profile_id == profile.id))
    chunks = chunk_cv(cv_text)
    if chunks:
        for text, vector in zip(chunks, embed(chunks)):
            db.add(CvChunk(profile_id=profile.id, text=text, embedding=vector))
    db.commit()
    return profile


def find_evidence(db: Session, queries: list[str], k: int = 2) -> list[list[tuple[str, float]]]:
    """For each query, return the k CV chunks closest in meaning, with a 0-1 similarity.

    `cosine_distance` becomes the pgvector operator `<=>`; similarity = 1 - distance.
    """
    if not queries:
        return []
    results = []
    for vector in embed(queries):
        distance = CvChunk.embedding.cosine_distance(vector)
        rows = db.execute(
            select(CvChunk.text, distance.label("distance"))
            .where(CvChunk.profile_id == PROFILE_ID)
            .order_by(distance)
            .limit(k)
        ).all()
        results.append([(row.text, round(1 - row.distance, 3)) for row in rows])
    return results
