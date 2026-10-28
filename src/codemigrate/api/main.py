"""FastAPI application. Run: uvicorn codemigrate.api.main:app --port 8000"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

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


class SPAFiles(StaticFiles):
    """Static files that fall back to index.html, so client-side routes survive a reload."""

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as e:
            if e.status_code != 404 or path.replace("\\", "/").startswith("api/"):
                raise
            return await super().get_response("index.html", scope)


# Single-host deploys (e.g. the HF Space) serve the built frontend from here.
if os.path.isdir(WEB_DIR := os.getenv("WEB_DIR", "")):
    app.mount("/", SPAFiles(directory=WEB_DIR, html=True), name="web")
