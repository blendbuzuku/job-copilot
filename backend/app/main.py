"""FastAPI entry point. Run with: uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import cv_store
from .config import settings
from .cv_parser import extract_text
from .db import get_db, init_db
from .schemas import ProfileIn, ProfileOut


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
    return {"status": "ok"}


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
