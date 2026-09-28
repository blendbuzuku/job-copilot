"""Tests the agent's flow with a fake LLM, so no API key or network is needed."""
from app.agent import build_agent

from .fakes import FakeLLM


def fake_evidence(queries):
    return [[(f"CV line about {q}", 0.8)] for q in queries]


def run(llm):
    agent = build_agent(llm, fake_evidence)
    return agent.invoke({"job_text": "We need Python...", "cv_text": "Jane Doe, Python dev"})


def test_full_run_produces_everything():
    result = run(FakeLLM(fact_problems_per_check=[[]]))
    assert result["company"] == "Acme"
    assert result["tailored_cv"] == "cv text"
    assert result["cover_letter"] == "cover_letter text"
    # must=2 points each, nice=1: matched 4 of 5 points
    assert result["match_score"] == 80
    assert result["matches"][0]["evidence"] == ["CV line about Python"]


def test_cv_is_rewritten_once_when_fact_check_finds_problems():
    llm = FakeLLM(fact_problems_per_check=[["Claims 10 years of Go"], []])
    result = run(llm)
    assert result["cv_attempts"] == 2
    assert llm.calls.count("cv") == 2


def test_rewrites_stop_after_two_attempts():
    llm = FakeLLM(fact_problems_per_check=[["bad"], ["still bad"]])
    result = run(llm)
    assert result["cv_attempts"] == 2
    assert result["fact_problems"] == ["still bad"]
