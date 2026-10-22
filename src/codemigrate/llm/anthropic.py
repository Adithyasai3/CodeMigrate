"""Anthropic adapter. Model name comes from ANTHROPIC_MODEL."""

from __future__ import annotations

import os

from codemigrate.llm.base import LLMClient, LLMResponse


class AnthropicClient(LLMClient):
    provider = "anthropic"

    def __init__(self, model: str | None = None, **kw) -> None:
        import anthropic

        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set (see .env.example)")
        model = model or os.getenv("ANTHROPIC_MODEL")
        if not model:
            raise RuntimeError("ANTHROPIC_MODEL is not set")
        super().__init__(model, **kw)
        self._client = anthropic.Anthropic()

    def _call(self, system, prompt, temperature, seed, json_mode) -> LLMResponse:
        # The Messages API has no seed parameter; reproducibility comes from the disk cache.
        msg = self._client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        return LLMResponse(
            text=text,
            model=self.model,
            prompt_tokens=msg.usage.input_tokens,
            completion_tokens=msg.usage.output_tokens,
        )
