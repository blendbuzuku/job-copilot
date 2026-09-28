"""A thin wrapper around the Anthropic SDK, so the agent code stays simple.

Two helpers:
- structured(): Claude replies with JSON that is validated against a Pydantic class.
- text(): Claude replies with free text (used for the CV and the cover letter).
"""
from typing import TypeVar

import anthropic
from pydantic import BaseModel

from .config import settings

T = TypeVar("T", bound=BaseModel)

# If Claude declines a request, the API automatically retries it on a
# recommended fallback model instead of returning an empty answer.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LLMError(RuntimeError):
    pass


class ClaudeLLM:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.client = anthropic.Anthropic(api_key=api_key or settings.anthropic_api_key or None)
        self.model = model or settings.claude_model

    def _request(self, method, system: str, prompt: str, **kwargs):
        response = method(
            model=self.model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            betas=[FALLBACK_BETA],
            fallbacks="default",
            **kwargs,
        )
        if response.stop_reason == "refusal":
            raise LLMError("Claude declined this request.")
        if response.stop_reason == "max_tokens":
            raise LLMError("Claude's answer was cut off because it was too long.")
        return response

    def structured(self, system: str, prompt: str, schema: type[T]) -> T:
        response = self._request(self.client.beta.messages.parse, system, prompt, output_format=schema)
        return response.parsed_output

    def text(self, system: str, prompt: str) -> str:
        response = self._request(self.client.beta.messages.create, system, prompt)
        return "".join(block.text for block in response.content if block.type == "text").strip()
