"""FastAPI entry point. Run with: uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import cv_store
from .agent import build_agent
from .config import settings
from .cv_parser import extract_text
from .db import get_db, init_db
from .demo_llm import DemoLLM
from .job_fetcher import JobFetchError, fetch_job_text
from .llm import ClaudeLLM, LLMError
from .models import Application
from .schemas import AnalyzeIn, ApplicationOut, ApplicationUpdate, ProfileIn, ProfileOut


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Job Copilot API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "demo_mode": settings.demo_mode}


# ---------- Profile (your base CV) ----------

def _profile_out(profile) -> ProfileOut:
    return ProfileOut(name=profile.name, cv_text=profile.cv_text, chunk_count=len(profile.chunks))


@app.get("/api/profile", response_model=ProfileOut)
def read_profile(db: Session = Depends(get_db)):
    return _profile_out(cv_store.get_profile(db))


@app.put("/api/profile", response_model=ProfileOut)
def update_profile(body: ProfileIn, db: Session = Depends(get_db)):
    return _profile_out(cv_store.save_cv(db, body.cv_text, body.name))


@app.post("/api/profile/upload", response_model=ProfileOut)
async def upload_cv(file: UploadFile, db: Session = Depends(get_db)):
    text = extract_text(file.filename or "", await file.read())
    if not text:
        raise HTTPException(400, "Couldn't read any text from that file. Try a .pdf, .txt or .md file.")
    return _profile_out(cv_store.save_cv(db, text))


# ---------- Applications ----------

@lru_cache
def get_llm() -> ClaudeLLM | DemoLLM:
    # Without an API key, fall back to free demo answers so the app can still be tried
    return DemoLLM() if settings.demo_mode else ClaudeLLM()


@app.post("/api/applications/analyze", response_model=ApplicationOut)
def analyze_job(body: AnalyzeIn, db: Session = Depends(get_db), llm: ClaudeLLM | DemoLLM = Depends(get_llm)):
    """Run the AI agent on a job posting and save the result as a new application."""
    profile = cv_store.get_profile(db)
    if not profile.cv_text.strip():
        raise HTTPException(400, "Upload your CV first.")

    try:
        job_text = body.job_text.strip() or fetch_job_text(body.job_url.strip())
    except JobFetchError as e:
        raise HTTPException(400, str(e))

    agent = build_agent(llm, lambda queries: cv_store.find_evidence(db, queries))
    try:
        result = agent.invoke({"job_text": job_text, "cv_text": profile.cv_text})
    except LLMError as e:
        raise HTTPException(502, str(e))

    application = Application(
        company=result.get("company", ""),
        role=result.get("role", ""),
        job_url=body.job_url.strip(),
        job_text=job_text,
        match_score=result.get("match_score", 0),
        matches=result.get("matches", []),
        tailored_cv=result.get("tailored_cv", ""),
        cover_letter=result.get("cover_letter", ""),
    )
    db.add(application)
    db.commit()
    return application


@app.get("/api/applications", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db)):
    return db.scalars(select(Application).order_by(Application.created_at.desc())).all()


def _get_application(db: Session, application_id: int) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(404, "Application not found")
    return application


@app.get("/api/applications/{application_id}", response_model=ApplicationOut)
def read_application(application_id: int, db: Session = Depends(get_db)):
    return _get_application(db, application_id)


@app.patch("/api/applications/{application_id}", response_model=ApplicationOut)
def update_application(application_id: int, body: ApplicationUpdate, db: Session = Depends(get_db)):
    application = _get_application(db, application_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(application, field, value)
    db.commit()
    db.refresh(application)
    return application


@app.delete("/api/applications/{application_id}", status_code=204)
def delete_application(application_id: int, db: Session = Depends(get_db)):
    db.delete(_get_application(db, application_id))
    db.commit()
