# Learning guide

This file explains how Job Copilot is built, one step at a time. Each step matches a
commit, so you can run `git log` and `git show <commit>` to see exactly what changed.

---

## Step 1: Backend skeleton and database

**Files to open:** `docker-compose.yml`, `backend/app/config.py`, `backend/app/db.py`,
`backend/app/models.py`, `backend/app/main.py`

### The big picture

```
Browser (React)  ──HTTP──▶  FastAPI (Python)  ──▶  PostgreSQL + pgvector
                                   │
                                   └──▶  Claude API (via a LangGraph agent)
```

### What each file does

- **`docker-compose.yml`** starts two containers: the database (`db`) and the Python API
  (`backend`). The image `pgvector/pgvector` is normal PostgreSQL with the vector
  extension already installed, so you don't have to install anything yourself.
- **`config.py`** reads settings from environment variables using `pydantic-settings`.
  Secrets like your API key live in a `.env` file that is never committed (see
  `.gitignore`). `.env.example` shows which values you need.
- **`db.py`** creates the SQLAlchemy *engine* (the connection pool) and `get_db()`, which
  FastAPI calls to give each request its own database session. `init_db()` turns on the
  `vector` extension and creates the tables.
- **`models.py`** defines the three tables as Python classes (this is the *ORM* pattern):
  - `Profile`: your base CV.
  - `CvChunk`: your CV cut into small pieces. Each piece has an **embedding**, a list of
    384 numbers that captures its meaning. Pieces with similar meaning have similar numbers.
  - `Application`: a job you are applying to, plus the AI's results and a status.
- **`main.py`** creates the FastAPI app. `lifespan` runs `init_db()` once at startup. The
  CORS middleware lets the React app (on port 5173) call the API (on port 8000).

### Key idea: why pgvector?

A normal database can find rows where `text = 'Python'`. It cannot find "the line in my CV
that best proves *experience building REST APIs*" when the CV says *"Built a FastAPI service
for payments"*. Embeddings turn text into vectors, and pgvector can sort rows by how close
their vectors are (`ORDER BY embedding <=> query`). That is called **semantic search**,
and it's the same technique behind RAG (retrieval-augmented generation).

### Try it

```powershell
docker compose up db -d          # start only the database
cd backend
python -m venv .venv
.venv\Scripts\activate           # Windows PowerShell
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs to see the interactive API docs. `/api/health` should
return `{"status": "ok"}`.

---

## Step 2: Upload your CV and search it by meaning

**Files to open:** `backend/app/cv_parser.py`, `backend/app/embeddings.py`,
`backend/app/cv_store.py`, `backend/app/main.py` (the "Profile" section),
`backend/tests/test_cv_parser.py`

### The flow

```
Upload CV (PDF/TXT) ─▶ extract text ─▶ split into chunks ─▶ embed each chunk ─▶ save in Postgres
                                                                                  │
"experience with Docker?" ─▶ embed the question ─▶ pgvector finds nearest chunks ◀┘
```

### What each file does

- **`cv_parser.py`**: `extract_text()` reads a PDF with `pypdf` (or decodes a text file).
  `chunk_cv()` splits the CV so that each bullet point or short paragraph becomes one chunk.
  Small chunks make search precise.
- **`embeddings.py`**: turns text into vectors with **fastembed**, a small model that runs
  on your own CPU (no API key, no cost). `@lru_cache` makes sure the model is loaded only
  once. The first run downloads it (about 130 MB).
- **`cv_store.py`**:
  - `save_cv()` stores the CV, deletes the old chunks, and saves new chunks with their vectors.
  - `find_evidence()` is the semantic search. `CvChunk.embedding.cosine_distance(vector)`
    becomes the SQL operator `<=>`, and `ORDER BY` it returns the closest chunks first.
    Similarity = 1 − distance, so 1.0 means "same meaning".
- **`main.py`**: three new endpoints:
  - `GET /api/profile`: read your CV
  - `PUT /api/profile`: save CV text you pasted
  - `POST /api/profile/upload`: upload a file
- **`schemas.py`**: Pydantic classes that define (and validate) the JSON going in and out.

### Key idea: dependency injection in FastAPI

`db: Session = Depends(get_db)` tells FastAPI: "before calling this function, call
`get_db()` and pass me what it yields". That way every request gets a fresh database
session and it's always closed afterwards, with no repeated code.

### Try it

Run the tests: `python -m pytest`

Start the API, open http://localhost:8000/docs, and use **POST /api/profile/upload**
with your own CV. The response shows how many chunks it made.
