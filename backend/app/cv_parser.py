"""Turn an uploaded CV into plain text, and split that text into small chunks."""
import io
import re

from pypdf import PdfReader


def extract_text(filename: str, data: bytes) -> str:
    """Read text from a PDF, or decode a .txt / .md file."""
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    return data.decode("utf-8", errors="ignore").strip()


# Bullet characters people commonly use in CVs
_BULLET = re.compile(r"^\s*([-*•●▪–]|\d+[.)])\s+")


def chunk_cv(text: str, min_len: int = 25, max_len: int = 400) -> list[str]:
    """Split a CV into chunks of roughly one bullet point or short paragraph each.

    Small chunks make search precise: when we look for "experience with Docker" we
    want the one line that proves it, not a whole page.
    """
    chunks: list[str] = []
    current = ""

    def flush():
        nonlocal current
        piece = " ".join(current.split())
        if len(piece) >= min_len:
            chunks.append(piece[:max_len])
        current = ""

    for line in text.splitlines():
        if not line.strip():
            flush()
        elif _BULLET.match(line):
            flush()
            current = _BULLET.sub("", line)
        else:
            current = f"{current} {line}" if current else line
            if len(current) > max_len:
                flush()
    flush()
    return chunks
