"""OpenAI adapter; also works with OpenAI-compatible endpoints (e.g. Groq) via OPENAI_BASE_URL."""

from __future__ import annotations

import os

from codemigrate.llm.base import LLMClient, LLMResponse


class OpenAIClient(LLMClient):
    provider = "openai"

    def __init__(self, model: str | None = None, **kw) -> None:
        import openai

        key = os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY (or GROQ_API_KEY) is not set")
        model = model or os.getenv("OPENAI_MODEL")
        if not model:
            raise RuntimeError("OPENAI_MODEL is not set")
        base_url = os.getenv("OPENAI_BASE_URL") or (
            "https://api.groq.com/openai/v1" if os.getenv("GROQ_API_KEY") else None
        )
        super().__init__(model, **kw)
        if base_url:
            self.provider = "openai-compatible"
        self._client = openai.OpenAI(api_key=key, base_url=base_url)

    def _call(self, system, prompt, temperature, seed, json_mode) -> LLMResponse:
        kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
        r = self._client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            seed=seed,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            **kwargs,
        )
        return LLMResponse(
            text=r.choices[0].message.content or "",
            model=self.model,
            prompt_tokens=r.usage.prompt_tokens if r.usage else 0,
            completion_tokens=r.usage.completion_tokens if r.usage else 0,
        )
