"""Test doubles: a fake Claude and a fake embedding model."""
import hashlib

from app.agent import FactCheck, FitAssessment, JobAnalysis


class FakeLLM:
    def __init__(self, fact_problems_per_check=((),)):
        self.fact_problems = [list(p) for p in fact_problems_per_check]
        self.calls = []

    def structured(self, system, prompt, schema):
        self.calls.append(schema.__name__)
        if schema is JobAnalysis:
            return JobAnalysis.model_validate({
                "company": "Acme",
                "role": "Backend Engineer",
                "requirements": [
                    {"skill": "Python", "importance": "must"},
                    {"skill": "Kubernetes", "importance": "must"},
                    {"skill": "GraphQL", "importance": "nice"},
                ],
            })
        if schema is FitAssessment:
            return FitAssessment.model_validate({"fits": [
                {"skill": "Python", "matched": True, "note": "Built a FastAPI service"},
                {"skill": "Kubernetes", "matched": True, "note": "Migrated to Kubernetes"},
                {"skill": "GraphQL", "matched": False, "note": "Not mentioned"},
            ]})
        if schema is FactCheck:
            return FactCheck(problems=self.fact_problems.pop(0))
        raise AssertionError(schema)

    def text(self, system, prompt):
        kind = "cover_letter" if "cover letter" in prompt else "cv"
        self.calls.append(kind)
        return f"{kind} text"



def fake_embed(texts):
    """Bag-of-words vectors: texts sharing words end up close together."""
    vectors = []
    for text in texts:
        vector = [0.0] * 384
        for word in text.lower().replace(",", " ").split():
            vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % 384] += 1
        vectors.append(vector)
    return vectors
