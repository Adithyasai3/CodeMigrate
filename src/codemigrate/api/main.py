"""FastAPI application. Run: uvicorn codemigrate.api.main:app --port 8000"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from codemigrate.api.db import init_db
from codemigrate.api.routes import RESULTS, router

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if os.getenv("JWT_SECRET", "dev-only-secret") in {"dev-only-secret", "change-me"}:
        log.warning("JWT_SECRET is not set; using an insecure development secret")
    yield


app = FastAPI(title="CodeMigrate API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
(RESULTS / "figures").mkdir(parents=True, exist_ok=True)
app.mount("/results-files", StaticFiles(directory=RESULTS / "figures"), name="figures")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
