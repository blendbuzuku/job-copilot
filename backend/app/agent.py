"""The AI agent, built as a LangGraph graph.

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

Each box is a "node": a plain Python function that receives the shared state and returns
the fields it wants to update. LangGraph runs them in order, runs the parallel branches,
and handles the retry loop.
"""
from typing import Callable, Literal, Protocol, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

MAX_CV_ATTEMPTS = 2

# ---------- What Claude must return (structured outputs) ----------


class Requirement(BaseModel):
    skill: str = Field(description="One concrete requirement, e.g. 'Production experience with PostgreSQL'")
    importance: Literal["must", "nice"]


class JobAnalysis(BaseModel):
    company: str
    role: str
    requirements: list[Requirement]


class RequirementFit(BaseModel):
    skill: str
    matched: bool
    note: str = Field(description="One short sentence: what in the CV proves it, or what's missing")


class FitAssessment(BaseModel):
    fits: list[RequirementFit]


class FactCheck(BaseModel):
    problems: list[str] = Field(description="Claims in the tailored CV not supported by the original CV")


# ---------- The shared state that flows through the graph ----------


class AgentState(TypedDict, total=False):
    job_text: str
    cv_text: str
    company: str
    role: str
    requirements: list[dict]
    evidence: list[list[tuple[str, float]]]
    matches: list[dict]
    match_score: float
    tailored_cv: str
    fact_problems: list[str]
    cv_attempts: int
    cover_letter: str


class LLM(Protocol):
    def structured(self, system: str, prompt: str, schema): ...
    def text(self, system: str, prompt: str) -> str: ...


EvidenceFinder = Callable[[list[str]], list[list[tuple[str, float]]]]

HONESTY_RULE = (
    "Never invent experience, employers, dates, numbers, degrees or skills. "
    "You may only reword, reorder, and emphasise what is already in the candidate's CV."
)


def _requirements_block(state: AgentState) -> str:
    lines = []
    for m in state["matches"]:
        mark = "✓" if m["matched"] else "✗"
        lines.append(f"{mark} [{m['importance']}] {m['skill']}: {m['note']}")
    return "\n".join(lines)


def build_agent(llm: LLM, find_evidence: EvidenceFinder):
    """Create the graph. The LLM and the search function are passed in, so tests can use fakes."""

    def analyze_job(state: AgentState) -> AgentState:
        result = llm.structured(
            system="You extract hiring requirements from job postings.",
            prompt=(
                "List the company, the job title, and 5 to 12 concrete requirements from this "
                "job posting. Mark each as 'must' (required) or 'nice' (preferred/bonus). "
                "If the company isn't named, use an empty string.\n\n"
                f"<job_posting>\n{state['job_text']}\n</job_posting>"
            ),
            schema=JobAnalysis,
        )
        return {
            "company": result.company,
            "role": result.role,
            "requirements": [r.model_dump() for r in result.requirements],
        }

    def find_cv_evidence(state: AgentState) -> AgentState:
        # RAG step: pgvector finds the CV lines closest in meaning to each requirement
        return {"evidence": find_evidence([r["skill"] for r in state["requirements"]])}

    def assess_fit(state: AgentState) -> AgentState:
        blocks = []
        for req, hits in zip(state["requirements"], state["evidence"]):
            lines = "\n".join(f"  - {text}" for text, _ in hits) or "  (nothing found)"
            blocks.append(f"Requirement: {req['skill']}\nClosest CV lines:\n{lines}")
        result = llm.structured(
            system="You are a strict, fair recruiter.",
            prompt=(
                "For each requirement, in the same order and with the same wording, decide whether the candidate's CV shows it. Use the closest "
                "CV lines as your main evidence, and the full CV for context.\n\n"
                + "\n\n".join(blocks)
                + f"\n\n<full_cv>\n{state['cv_text']}\n</full_cv>"
            ),
            schema=FitAssessment,
        )
        by_skill = {f.skill.strip().lower(): f for f in result.fits}
        matches = []
        for i, (req, hits) in enumerate(zip(state["requirements"], state["evidence"])):
            # Claude answers in the same order; fall back to matching by name just in case
            fit = by_skill.get(req["skill"].strip().lower()) or (
                result.fits[i] if i < len(result.fits) else RequirementFit(skill=req["skill"], matched=False, note="Not assessed")
            )
            matches.append({
                **req,
                "matched": fit.matched,
                "note": fit.note,
                "evidence": [text for text, _ in hits],
                "similarity": hits[0][1] if hits else 0.0,
            })
        # Score: "must" requirements count double
        total = sum(2 if m["importance"] == "must" else 1 for m in matches) or 1
        got = sum(2 if m["importance"] == "must" else 1 for m in matches if m["matched"])
        return {"matches": matches, "match_score": round(100 * got / total)}

    def tailor_cv(state: AgentState) -> AgentState:
        feedback = ""
        if state.get("fact_problems"):
            feedback = (
                "\n\nYour previous draft had these unsupported claims. Remove or fix them:\n- "
                + "\n- ".join(state["fact_problems"])
            )
        cv = llm.text(
            system=f"You are an expert CV writer. {HONESTY_RULE}",
            prompt=(
                f"Rewrite this CV for the role of {state['role']} at {state['company'] or 'the company'}. "
                "Lead with the experience that matches the requirements, use the job's wording where "
                "it's truthful, and keep it to one page. Reply with the CV only, in Markdown.\n\n"
                f"<requirements>\n{_requirements_block(state)}\n</requirements>\n\n"
                f"<original_cv>\n{state['cv_text']}\n</original_cv>{feedback}"
            ),
        )
        return {"tailored_cv": cv, "cv_attempts": state.get("cv_attempts", 0) + 1}

    def check_facts(state: AgentState) -> AgentState:
        result = llm.structured(
            system="You are a meticulous fact-checker.",
            prompt=(
                "Compare the tailored CV with the original CV. List every claim in the tailored "
                "CV (skill, employer, title, date, number, achievement) that the original does "
                "not support. Rewording is fine. Return an empty list if everything is supported.\n\n"
                f"<original_cv>\n{state['cv_text']}\n</original_cv>\n\n"
                f"<tailored_cv>\n{state['tailored_cv']}\n</tailored_cv>"
            ),
            schema=FactCheck,
        )
        return {"fact_problems": result.problems}

    def needs_rewrite(state: AgentState) -> str:
        if state.get("fact_problems") and state.get("cv_attempts", 0) < MAX_CV_ATTEMPTS:
            return "tailor_cv"
        return END

    def write_cover_letter(state: AgentState) -> AgentState:
        letter = llm.text(
            system=f"You write warm, specific, concise cover letters. {HONESTY_RULE}",
            prompt=(
                f"Write a cover letter (under 300 words) for the role of {state['role']} at "
                f"{state['company'] or 'the company'}. Connect 2 or 3 of the candidate's strongest "
                "matching experiences to what the job needs. For missing requirements, show "
                "willingness to learn without pretending. No placeholders like [Your Name]: use the "
                "name from the CV, or sign off without a name. Reply with the letter only.\n\n"
                f"<requirements>\n{_requirements_block(state)}\n</requirements>\n\n"
                f"<cv>\n{state['cv_text']}\n</cv>\n\n<job_posting>\n{state['job_text']}\n</job_posting>"
            ),
        )
        return {"cover_letter": letter}

    graph = StateGraph(AgentState)
    graph.add_node("analyze_job", analyze_job)
    graph.add_node("find_evidence", find_cv_evidence)
    graph.add_node("assess_fit", assess_fit)
    graph.add_node("tailor_cv", tailor_cv)
    graph.add_node("check_facts", check_facts)
    graph.add_node("write_cover_letter", write_cover_letter)

    graph.add_edge(START, "analyze_job")
    graph.add_edge("analyze_job", "find_evidence")
    graph.add_edge("find_evidence", "assess_fit")
    # Two branches run in parallel after assess_fit
    graph.add_edge("assess_fit", "tailor_cv")
    graph.add_edge("assess_fit", "write_cover_letter")
    graph.add_edge("tailor_cv", "check_facts")
    graph.add_conditional_edges("check_facts", needs_rewrite, ["tailor_cv", END])
    graph.add_edge("write_cover_letter", END)
    return graph.compile()
