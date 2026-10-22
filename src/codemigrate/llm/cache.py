"""On-disk JSON cache for LLM calls keyed by a hash of (provider, model, params, prompt)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)


def cache_key(
    provider: str,
    model: str,
    system: str,
    prompt: str,
    temperature: float,
    seed: int | None,
    json_mode: bool,
) -> str:
    """Stable sha256 over everything that can change a completion."""
    payload = json.dumps(
        {
            "provider": provider,
            "model": model,
            "system": system,
            "prompt": prompt,
            "temperature": temperature,
            "seed": seed,
            "json_mode": json_mode,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class DiskCache:
    """One JSON file per key under ``root/<key[:2]>/<key>.json`` (atomic writes)."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> dict | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.error("corrupt cache entry %s: %s (ignored)", path, exc)
            return None

    def set(self, key: str, value: dict) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
