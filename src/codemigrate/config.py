"""Runtime configuration loaded from environment variables (and an optional .env file)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return value if value not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    """All tunables in one place; every field can be overridden through the environment."""

    repo_root: Path = REPO_ROOT
    kb_path: Path = field(
        default_factory=lambda: REPO_ROOT / "data" / "kb" / "django_changes.jsonl"
    )
    llm_provider: str = field(default_factory=lambda: _env("LLM_PROVIDER", "offline"))
    llm_max_calls: int = field(default_factory=lambda: int(_env("LLM_MAX_CALLS", "2000")))
    llm_max_cost_usd: float = field(default_factory=lambda: float(_env("LLM_MAX_COST_USD", "10")))
    llm_min_interval_s: float = field(
        default_factory=lambda: float(_env("LLM_MIN_INTERVAL_S", "4.5"))
    )
    llm_cache_dir: Path = field(
        default_factory=lambda: REPO_ROOT / _env("LLM_CACHE_DIR", ".cache/llm")
    )
    embedding_model: str = field(
        default_factory=lambda: _env("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    )
    database_url: str = field(
        default_factory=lambda: _env("DATABASE_URL", f"sqlite:///{REPO_ROOT / 'codemigrate.db'}")
    )
    jwt_secret: str = field(default_factory=lambda: _env("JWT_SECRET", "dev-only-secret"))
    seed: int = field(default_factory=lambda: int(_env("SEED", "42")))


def get_settings() -> Settings:
    """Return a fresh Settings snapshot (cheap; reads env each time so tests can monkeypatch)."""
    return Settings()
