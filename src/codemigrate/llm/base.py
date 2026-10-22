"""Provider-agnostic LLM interface with disk caching, budget caps, throttling and retries."""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from codemigrate.config import get_settings
from codemigrate.llm.cache import DiskCache, cache_key

log = logging.getLogger(__name__)


class BudgetExceeded(RuntimeError):
    """Raised when the configured call or cost cap would be exceeded."""


class LLMError(RuntimeError):
    """Raised when a provider call fails after retries."""


@dataclass
class LLMResponse:
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached: bool = False
    latency_s: float = 0.0


@dataclass
class UsageTracker:
    """Counts real (non-cached) calls, tokens and cost; enforces hard caps."""

    max_calls: int
    max_cost_usd: float
    price_in_per_mtok: float = 0.0
    price_out_per_mtok: float = 0.0
    calls: int = 0
    cached_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def check(self) -> None:
        if self.calls >= self.max_calls:
            raise BudgetExceeded(f"LLM call cap reached ({self.max_calls}); raise LLM_MAX_CALLS")
        if self.cost_usd >= self.max_cost_usd:
            raise BudgetExceeded(f"LLM cost cap reached (${self.max_cost_usd:.2f})")

    def record(self, resp: LLMResponse) -> None:
        with self._lock:
            if resp.cached:
                self.cached_calls += 1
                return
            self.calls += 1
            self.prompt_tokens += resp.prompt_tokens
            self.completion_tokens += resp.completion_tokens
            self.cost_usd += (
                resp.prompt_tokens * self.price_in_per_mtok
                + resp.completion_tokens * self.price_out_per_mtok
            ) / 1e6

    def snapshot(self) -> dict:
        return {
            "calls": self.calls,
            "cached_calls": self.cached_calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost_usd": round(self.cost_usd, 6),
        }


_TRACKER: UsageTracker | None = None


def global_tracker() -> UsageTracker:
    """Process-wide usage tracker (caps apply across all clients in one run)."""
    global _TRACKER
    if _TRACKER is None:
        s = get_settings()
        _TRACKER = UsageTracker(
            max_calls=s.llm_max_calls,
            max_cost_usd=s.llm_max_cost_usd,
            # Prices are user-configured; defaults are 0 (free tier). Never hardcoded here.
            price_in_per_mtok=float(os.getenv("LLM_PRICE_IN_PER_MTOK", "0") or 0),
            price_out_per_mtok=float(os.getenv("LLM_PRICE_OUT_PER_MTOK", "0") or 0),
        )
    return _TRACKER


class LLMClient(ABC):
    """Base client. Subclasses implement :meth:`_call`; :meth:`complete` adds cache/budget."""

    provider = "base"

    def __init__(
        self,
        model: str,
        tracker: UsageTracker | None = None,
        cache: DiskCache | None = None,
        min_interval_s: float | None = None,
    ) -> None:
        self.model = model
        self.tracker = tracker or global_tracker()
        self.cache = cache or DiskCache(get_settings().llm_cache_dir)
        self.min_interval_s = (
            get_settings().llm_min_interval_s if min_interval_s is None else min_interval_s
        )
        self._last_call = 0.0

    @abstractmethod
    def _call(
        self, system: str, prompt: str, temperature: float, seed: int | None, json_mode: bool
    ) -> LLMResponse:
        """Perform one provider request."""

    def complete(
        self,
        system: str,
        prompt: str,
        temperature: float = 0.0,
        seed: int | None = None,
        json_mode: bool = True,
        max_retries: int = 5,
    ) -> LLMResponse:
        """Cached, budgeted, throttled completion with exponential backoff on failures."""
        key = cache_key(self.provider, self.model, system, prompt, temperature, seed, json_mode)
        hit = self.cache.get(key)
        if hit is not None:
            resp = LLMResponse(**{**hit, "cached": True})
            self.tracker.record(resp)
            return resp
        self.tracker.check()
        delay = max(self.min_interval_s, 1.0)
        for attempt in range(1, max_retries + 1):
            wait = self.min_interval_s - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            t0 = time.monotonic()
            try:
                self._last_call = t0
                resp = self._call(system, prompt, temperature, seed, json_mode)
                resp.latency_s = time.monotonic() - t0
                break
            except BudgetExceeded:
                raise
            except Exception as exc:  # provider SDKs raise many types; all are logged
                retry_after = _retry_after_seconds(exc)
                log.warning(
                    "%s call failed (attempt %d/%d): %s",
                    self.provider,
                    attempt,
                    max_retries,
                    str(exc)[:300],
                )
                if attempt == max_retries:
                    raise LLMError(f"{self.provider}/{self.model}: {exc}") from exc
                time.sleep(retry_after or delay)
                delay = min(delay * 2, 120)
        self.tracker.record(resp)
        self.cache.set(
            key,
            {
                "text": resp.text,
                "model": resp.model,
                "prompt_tokens": resp.prompt_tokens,
                "completion_tokens": resp.completion_tokens,
                "latency_s": resp.latency_s,
            },
        )
        return resp


def _retry_after_seconds(exc: Exception) -> float | None:
    m = re.search(r"retry[^0-9]{0,20}(\d+(?:\.\d+)?)\s*s", str(exc), re.I)
    return float(m.group(1)) + 1 if m else None


def parse_json_object(text: str) -> dict:
    """Parse a JSON object from model output, tolerating ```json fences and leading prose."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise
        obj = json.loads(text[start : end + 1])
    if not isinstance(obj, dict):
        raise ValueError("expected a JSON object")
    return obj
