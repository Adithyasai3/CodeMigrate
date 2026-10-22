"""LLM clients. Use :func:`get_client` to build one by provider name."""

from __future__ import annotations

import os

from codemigrate.llm.base import LLMClient

PROVIDERS = ("offline", "gemini", "anthropic", "openai")


def get_client(provider: str | None = None, model: str | None = None) -> LLMClient:
    """Return a client for ``provider`` (default: LLM_PROVIDER env var, else offline)."""
    provider = (provider or os.getenv("LLM_PROVIDER") or "offline").lower()
    if provider == "offline":
        from codemigrate.llm.offline import OfflineClient

        return OfflineClient()
    if provider == "gemini":
        from codemigrate.llm.gemini import GeminiClient

        return GeminiClient(model)
    if provider == "anthropic":
        from codemigrate.llm.anthropic import AnthropicClient

        return AnthropicClient(model)
    if provider in {"openai", "groq"}:
        from codemigrate.llm.openai import OpenAIClient

        return OpenAIClient(model)
    raise ValueError(f"unknown provider {provider!r}; choose from {PROVIDERS}")


def available_providers() -> list[str]:
    """Providers whose API keys are present (offline is always available)."""
    out = ["offline"]
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        out.append("gemini")
    if os.getenv("ANTHROPIC_API_KEY") and os.getenv("ANTHROPIC_MODEL"):
        out.append("anthropic")
    if (os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY")) and os.getenv("OPENAI_MODEL"):
        out.append("openai")
    return out
