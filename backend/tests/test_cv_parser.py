from app.cv_parser import chunk_cv, extract_text

CV = """Jane Doe
Backend developer

Experience
- Built a FastAPI service that processes 2M payments per day
- Migrated the team's deployments to Docker and Kubernetes
• Mentored 3 junior developers

Skills
Python, PostgreSQL, React, AWS
"""


def test_each_bullet_becomes_its_own_chunk():
    chunks = chunk_cv(CV)
    assert "Built a FastAPI service that processes 2M payments per day" in chunks
    assert "Migrated the team's deployments to Docker and Kubernetes" in chunks


def test_short_fragments_are_dropped():
    assert "Experience" not in chunk_cv(CV)


def test_plain_text_is_decoded():
    assert extract_text("cv.txt", "héllo".encode()) == "héllo"
