"""Google Gemini adapter (google-genai SDK). Model name comes from GEMINI_MODEL."""

from __future__ import annotations

import os

from codemigrate.llm.base import LLMClient, LLMResponse


class GeminiClient(LLMClient):
    provider = "gemini"

    def __init__(self, model: str | None = None, **kw) -> None:
        from google import genai

        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set (see .env.example)")
        super().__init__(model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), **kw)
        self._client = genai.Client(api_key=key)

    def _call(self, system, prompt, temperature, seed, json_mode) -> LLMResponse:
        from google.genai import types

        cfg = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            seed=seed,
            response_mime_type="application/json" if json_mode else "text/plain",
        )
        r = self._client.models.generate_content(model=self.model, contents=prompt, config=cfg)
        usage = r.usage_metadata
        text = r.text
        if text is None:
            raise RuntimeError(f"empty Gemini response (finish={_finish(r)})")
        return LLMResponse(
            text=text,
            model=self.model,
            prompt_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            completion_tokens=(getattr(usage, "candidates_token_count", 0) or 0)
            + (getattr(usage, "thoughts_token_count", 0) or 0),
        )


def _finish(r) -> str:
    try:
        return str(r.candidates[0].finish_reason)
    except (AttributeError, IndexError, TypeError):
        return "unknown"
