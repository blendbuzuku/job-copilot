"""Demo mode: a stand-in for Claude that needs no API key and costs nothing.

It gives simple, rule-based answers (keyword matching and templates) so you can try
every screen of the app. Add an API key to .env to get real AI results.
"""
import re

from .agent import FactCheck, FitAssessment, JobAnalysis

# Skills the demo knows how to spot in a job posting
KNOWN_SKILLS = [
    "Python", "Java", "JavaScript", "TypeScript", "C#", "Go", "SQL", "PostgreSQL", "MySQL",
    "MongoDB", "Redis", "React", "Angular", "Vue", "Node.js", "Next.js", "FastAPI", "Django",
    "Flask", ".NET", "Spring", "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Terraform",
    "CI/CD", "Git", "REST", "GraphQL", "Microservices", "Machine Learning", "LLM", "Agile",
    "Linux", "Kafka", "Excel", "Power BI", "Tableau", "Communication", "Leadership",
]
NICE_HINTS = ("nice to have", "bonus", "plus", "preferred", "desirable", "advantage")


def _mentions(text: str, skill: str) -> bool:
    return re.search(rf"(?<![\w.]){re.escape(skill.lower())}(?![\w])", text.lower()) is not None


def _between(prompt: str, tag: str) -> str:
    match = re.search(rf"<{tag}>\n(.*?)\n</{tag}>", prompt, re.S)
    return match.group(1) if match else ""


class DemoLLM:
    def structured(self, system: str, prompt: str, schema):
        if schema is JobAnalysis:
            job = _between(prompt, "job_posting")
            requirements = []
            for skill in KNOWN_SKILLS:
                if _mentions(job, skill):
                    line = next((l for l in job.lower().splitlines() if skill.lower() in l), "")
                    nice = any(hint in line for hint in NICE_HINTS)
                    requirements.append({"skill": skill, "importance": "nice" if nice else "must"})
            first_line = next((l.strip() for l in job.splitlines() if l.strip()), "Demo role")
            return JobAnalysis.model_validate({
                "company": "",
                "role": first_line[:80],
                "requirements": requirements[:12] or [{"skill": "Communication", "importance": "must"}],
            })

        if schema is FitAssessment:
            cv = _between(prompt, "full_cv")
            skills = re.findall(r"^Requirement: (.+)$", prompt, re.M)
            return FitAssessment.model_validate({"fits": [
                {
                    "skill": s,
                    "matched": _mentions(cv, s),
                    "note": "Your CV mentions it (demo check)." if _mentions(cv, s) else "Not found in your CV (demo check).",
                }
                for s in skills
            ]})

        if schema is FactCheck:
            return FactCheck(problems=[])
        raise ValueError(f"Demo mode can't answer {schema.__name__}")

    def text(self, system: str, prompt: str) -> str:
        banner = "> **Demo mode:** add an Anthropic API key to .env to get a real AI-written version.\n\n"
        if "cover letter" in prompt:
            return banner + (
                "Dear hiring team,\n\n"
                "I'm excited to apply for this role. My experience matches several of the key "
                "requirements, and I'd welcome the chance to bring it to your team.\n\n"
                "Thank you for your time and consideration.\n\nKind regards"
            )
        return banner + _between(prompt, "original_cv")
