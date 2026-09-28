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
