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

---

## Step 3: The AI agent (LangGraph + Claude)

**Files to open:** `backend/app/agent.py` (start with the diagram at the top),
`backend/app/llm.py`, `backend/tests/test_agent.py`

### The graph

```
    analyze_job          read the posting, list its requirements
         |
    find_evidence        pgvector: closest CV lines for each requirement (RAG)
         |
    assess_fit           Claude decides which requirements the CV really shows
       /    \
tailor_cv    write_cover_letter      (these two branches run in parallel)
     |
check_facts  ---(unsupported claims? rewrite once)---> back to tailor_cv
     |
    END
```

### Key ideas

- **State:** `AgentState` is a dictionary that flows through the graph. Each node is a
  normal function: it reads the state and returns only the fields it changes. LangGraph
  merges them in.
- **Edges:** `add_edge(a, b)` means "after a, run b". Two edges out of `assess_fit` make
  the CV and the cover letter run **in parallel**. `add_conditional_edges` lets a function
  (`needs_rewrite`) choose the next node, and that's how the **retry loop** works.
- **Why a graph and not one big prompt?** Each step is small, testable, and easy to
  improve on its own. The fact-check loop is something a single prompt can't do: the
  agent checks its own work and fixes it. This pattern (plan → act → verify → retry) is
  what "agentic AI" means in job postings.
- **RAG (retrieval-augmented generation):** `find_evidence` pulls the most relevant CV lines
  from pgvector and puts them in front of Claude in `assess_fit`. Claude judges using real
  evidence instead of guessing.
- **Structured outputs:** `llm.structured(..., schema=JobAnalysis)` makes Claude reply with
  JSON that matches the Pydantic class, and the SDK validates it for you. No fragile text
  parsing.
- **Guardrail:** `HONESTY_RULE` is in every writing prompt, and `check_facts` enforces it.
  The AI may reword your experience but must never invent it.
- **Fallbacks:** in `llm.py`, `fallbacks="default"` tells the Claude API to retry on another
  model automatically if a request is declined.

### Key idea: dependency injection for testing

`build_agent(llm, find_evidence)` receives the LLM and the search function as arguments
instead of creating them itself. In `test_agent.py` we pass a `FakeLLM` that returns canned
answers, so the tests run instantly, cost nothing, and need no API key. They check the
*flow*: the score maths, that the rewrite happens, and that the loop stops after 2 attempts.

### Try it

`python -m pytest -v`

---

## Step 4: API endpoints for applications

**Files to open:** `backend/app/main.py` (the "Applications" section),
`backend/app/schemas.py`, `backend/app/job_fetcher.py`, `backend/tests/test_api.py`

### The endpoints (a REST API)

| Method | Path | What it does |
|---|---|---|
| `POST` | `/api/applications/analyze` | Run the agent on a job link or pasted text, save the result |
| `GET` | `/api/applications` | List all applications (newest first) |
| `GET` | `/api/applications/{id}` | One application |
| `PATCH` | `/api/applications/{id}` | Change some fields, e.g. `{"status": "applied"}` |
| `DELETE` | `/api/applications/{id}` | Remove it |

REST convention: the **URL names the thing** (`/applications/7`) and the **HTTP method
says what to do** with it. `PATCH` changes only the fields you send, and that's why
`ApplicationUpdate` uses `exclude_unset=True`.

### Key ideas

- **Validation for free:** `status: Status` is a `Literal[...]`, so FastAPI rejects
  `"ghosted"` with a 422 error before your code even runs. `AnalyzeIn` has a
  `model_validator` that requires either a link or text.
- **`response_model=ApplicationOut`** converts the database object to JSON and hides
  anything not listed in the schema.
- **`job_fetcher.py`** downloads the page with `httpx`, then BeautifulSoup removes scripts,
  menus and footers so Claude gets just the posting. Some sites (like LinkedIn) need a
  login, so the app tells you to paste the text instead.
- **Testing with overrides:** `app.dependency_overrides[get_llm] = ...` swaps the real
  Claude client for the fake one, only in tests. The API tests use a real Postgres
  and skip themselves if it isn't running.

### Try it

1. `docker compose up db -d`, then start the API.
2. Copy `.env.example` to `.env` and add your Anthropic API key.
3. In http://localhost:8000/docs: upload your CV, then call `POST /api/applications/analyze`
   with `{"job_text": "<paste a real job posting>"}`. It takes up to a minute or two,
   because it makes several Claude calls.

---

## Step 5: The React frontend

**Files to open, in this order:** `frontend/src/main.tsx`, `frontend/src/App.tsx`,
`frontend/src/api.ts`, then the pages in `frontend/src/pages/`

### The pages

| Route | File | What you see |
|---|---|---|
| `/` | `BoardPage.tsx` | Your applications in columns by status |
| `/new` | `NewApplicationPage.tsx` | Paste a job link or text and run the agent |
| `/applications/:id` | `ApplicationPage.tsx` | Match score, gaps, tailored CV and cover letter |
| `/profile` | `ProfilePage.tsx` | Upload or paste your CV |

### Key ideas

- **Vite** is the dev server and build tool. `npm run dev` starts it with instant reload.
  In `vite.config.ts`, the `proxy` forwards every `/api/...` request to FastAPI, so the
  browser only ever talks to one address (no CORS problems in development).
- **TypeScript types mirror the backend:** the interfaces in `api.ts` match `schemas.py`.
  If you misspell a field, the editor underlines it before you even run the app.
- **React Router** (`App.tsx`) maps URLs to pages. `useParams()` reads `:id` from the URL.
- **TanStack Query** handles all server data:
  - `useQuery({ queryKey, queryFn })` loads data and gives you `isPending`, `error` and `data`.
    It also caches it, so going back to a page is instant.
  - `useMutation` is for requests that *change* data (save, update, delete).
  - After a change, `invalidateQueries(['applications'])` tells every page showing that
    list to refetch it. That's how the board updates after you move a card.
- **Tailwind CSS:** styling with small utility classes right in the JSX
  (`rounded-md bg-indigo-600 px-4 py-2`). No separate CSS files to keep in sync.
- **Download PDF** (`lib/print.ts`) opens the CV in a clean window and calls `print()`.
  Choose "Save as PDF" in the dialog. It's simple, and you don't need a PDF library.

### A bug worth learning from

The first version of `ProfilePage` gave the editor `key={profile.cv_text}`. After saving,
the text changed, so the key changed, so React threw away the component *and its
"Saved!" message*. The fix: create the editor once and update its text in the mutation's
`onSuccess`. Lesson: changing a `key` resets a component's state completely.

### Try it

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 (the backend must be running on port 8000).

---

## Step 6: Continuous integration (GitHub Actions)

**File to open:** `.github/workflows/ci.yml`

Every push to GitHub now runs three jobs on GitHub's servers:

1. **backend**: starts a real Postgres + pgvector (`services:`), installs Python packages,
   and runs `pytest`.
2. **frontend**: installs packages with `npm ci`, runs the linter, and builds the app
   (which also type-checks all the TypeScript).
3. **docker**: builds both Docker images, so you know `docker compose up` will work.

See the results in the **Actions** tab of the repo on GitHub. A green check next to a commit
means everything passed. This is what "CI/CD" means in job postings: the *CI* part checks
every change automatically; *CD* (continuous deployment) would also ship it to a server.

---

## Where to go next

Ideas to extend the project (and your CV):

- **Streaming progress:** send each agent step to the browser as it happens with
  Server-Sent Events, instead of a fake progress timer.
- **User accounts:** add login (e.g. JWT auth in FastAPI) so several people can use it.
- **Deploy to AWS:** run the containers on AWS (ECS or App Runner) with a managed Postgres (RDS).
- **Interview prep:** a new LangGraph node that writes likely interview questions for each role.
- **Browser extension:** analyze a job directly from the job site.

---

## Step 7: Free demo mode

**Files to open:** `backend/app/demo_llm.py`, `get_llm()` in `backend/app/main.py`,
`demo_mode` in `backend/app/config.py`, the banner in `frontend/src/App.tsx`

With no API key in `.env`, the backend swaps Claude for `DemoLLM`, which answers with
simple rules: keyword matching for skills and templates for the documents. The rest of the
app (pgvector, LangGraph, database, frontend) runs for real.

This works because of the **dependency injection** from step 3: the agent only needs
*something* with `structured()` and `text()` methods, and it doesn't care whether that's
Claude, a test fake, or the demo. Swapping one piece without touching the rest is the payoff
of that design.
