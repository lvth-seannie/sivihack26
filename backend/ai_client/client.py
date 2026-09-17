"""Thin wrapper around the Gemini API. Feature code calls `generate()` here
and never imports google.generativeai directly, so the provider/model
lives in one place and can be swapped without touching callers (per the
project's original "ai_client - LLM provider wrapper" plan).

Uses the Gemini Developer API: the key provisioned for this hackathon is
a Google AI Studio key (AIzaSy...), not an Anthropic one. Note that
`google-generativeai` itself is deprecated upstream in favor of
`google-genai`, but it's what's installed and confirmed working against
this key - swapping SDKs later only touches this file.
"""

import json
from typing import Optional, Type, TypeVar

import google.generativeai as genai
from decouple import config as env
from pydantic import BaseModel

MODEL = "gemini-3.6-flash"

T = TypeVar("T", bound=BaseModel)

_configured = False


def _ensure_configured() -> None:
    global _configured
    if not _configured:
        genai.configure(api_key=env("GEMINI_API_KEY"))
        _configured = True


def generate(prompt: str, *, output_format: Type[T], system: Optional[str] = None) -> T:
    """Sends `prompt` to Gemini and returns a validated instance of
    `output_format` (a Pydantic model) - the only way feature code should
    call the LLM. Raises on a malformed/non-JSON response or a schema
    mismatch - callers decide how to handle it (extract_tender_data.py
    logs and continues the batch)."""

    _ensure_configured()
    model = genai.GenerativeModel(MODEL, system_instruction=system)
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(response_mime_type="application/json"),
    )
    return output_format.model_validate(json.loads(response.text))
