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
        self._client = openai.OpenAI(api_key=key, base_url=base_url, timeout=180.0)

    def _call(self, system, prompt, temperature, seed, json_mode) -> LLMResponse:
        # Some routed models reject response_format; replies are still parsed as JSON (+ retries).
        use_json_mode = json_mode and os.getenv("OPENAI_JSON_MODE", "1") != "0"
        kwargs = {"response_format": {"type": "json_object"}} if use_json_mode else {}
        # Groq's free tier counts prompt + max_tokens against an 8k tokens/minute limit,
        # so the reply length has to be capped there; reasoning models also accept an effort.
        if max_tokens := os.getenv("OPENAI_MAX_TOKENS"):
            kwargs["max_tokens"] = int(max_tokens)
        if effort := os.getenv("OPENAI_REASONING_EFFORT"):
            kwargs["reasoning_effort"] = effort
        r = self._client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            seed=seed,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            **kwargs,
        )
        return LLMResponse(
            text=r.choices[0].message.content or "",
            # the model that actually answered (routers may name the upstream model)
            model=r.model or self.model,
            prompt_tokens=r.usage.prompt_tokens if r.usage else 0,
            completion_tokens=r.usage.completion_tokens if r.usage else 0,
        )
