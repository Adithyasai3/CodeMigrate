import json

import pytest

from codemigrate.llm.base import (
    BudgetExceeded,
    LLMClient,
    LLMResponse,
    UsageTracker,
    parse_json_object,
)
from codemigrate.llm.cache import DiskCache
from codemigrate.llm.offline import argument_condition
from codemigrate.llm.reasoner import ReasonerStats, reason_llm_only


class FakeClient(LLMClient):
    provider = "fake"

    def __init__(self, replies, tmp_path, max_calls=100):
        tracker = UsageTracker(max_calls=max_calls, max_cost_usd=1.0, price_in_per_mtok=1.0)
        super().__init__("fake-1", tracker=tracker, cache=DiskCache(tmp_path), min_interval_s=0)
        self.replies = list(replies)
        self.n = 0

    def _call(self, system, prompt, temperature, seed, json_mode):
        self.n += 1
        return LLMResponse(
            text=self.replies.pop(0), model=self.model, prompt_tokens=10, completion_tokens=5
        )


def test_cache_hit_avoids_second_call(tmp_path):
    c = FakeClient(['{"findings": []}'], tmp_path)
    a = c.complete("s", "p")
    b = c.complete("s", "p")
    assert c.n == 1 and not a.cached and b.cached
    assert c.tracker.calls == 1 and c.tracker.cached_calls == 1
    assert c.tracker.cost_usd == pytest.approx(10 / 1e6)


def test_cache_key_depends_on_params(tmp_path):
    c = FakeClient(['{"a":1}', '{"a":2}'], tmp_path)
    c.complete("s", "p", seed=1)
    c.complete("s", "p", seed=2)
    assert c.n == 2


def test_call_cap_enforced(tmp_path):
    c = FakeClient(["{}", "{}"], tmp_path, max_calls=1)
    c.complete("s", "p1")
    with pytest.raises(BudgetExceeded):
        c.complete("s", "p2")


def test_parse_json_variants():
    assert parse_json_object('```json\n{"findings": []}\n```') == {"findings": []}
    assert parse_json_object('Sure! {"findings": [1]} done') == {"findings": [1]}
    with pytest.raises(ValueError):
        parse_json_object("no json here")


def test_reasoner_retries_invalid_json(tmp_path):
    good = json.dumps(
        {"findings": [{"line": 2, "symbol": "django.x", "explanation": "e", "cited_ids": []}]}
    )
    c = FakeClient(["not json", good], tmp_path)
    stats = ReasonerStats()
    out = reason_llm_only(c, "a.py", "x = 1\ny = 2\n", "4.0", "5.1", stats=stats)
    assert stats.invalid_json == 1 and len(out) == 1 and out[0].line == 2


def test_argument_condition():
    assert argument_condition("The is_dst argument is removed from: Trunc()") == (
        "kwarg",
        {"is_dst"},
    )
    cond = argument_condition("Passing positional arguments to Signer is deprecated")
    assert cond[0] == "positional"
    assert argument_condition("django.utils.baseconv module is removed.") is None
