"""Download a job posting from a URL and keep only the readable text."""
import httpx
from bs4 import BeautifulSoup

MAX_CHARS = 20_000


class JobFetchError(RuntimeError):
    pass


def fetch_job_text(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        raise JobFetchError("The link must start with http:// or https://")
    try:
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (JobCopilot)"},
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        raise JobFetchError(f"Couldn't download that page ({e}). Paste the job text instead.") from e

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "svg"]):
        tag.decompose()
    lines = (line.strip() for line in soup.get_text("\n").splitlines())
    text = "\n".join(line for line in lines if line)
    if len(text) < 200:
        raise JobFetchError("That page had almost no text (it may need a login). Paste the job text instead.")
    return text[:MAX_CHARS]
