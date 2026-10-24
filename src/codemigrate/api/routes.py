"""HTTP routes: auth, projects, scans (JSON or zip upload), reports, benchmark results."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import PlainTextResponse, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from codemigrate.analysis.repo_scanner import iter_sources
from codemigrate.api import jobs
from codemigrate.api.auth import create_token, current_user, hash_password, verify_password
from codemigrate.api.db import get_session
from codemigrate.api.models import (
    Project,
    ProjectIn,
    ProjectOut,
    RegisterIn,
    Scan,
    ScanDetail,
    ScanIn,
    ScanOut,
    SourceFile,
    TokenOut,
    User,
    UserOut,
)
from codemigrate.api.reports import to_markdown, to_pdf
from codemigrate.config import REPO_ROOT
from codemigrate.kb.versions import supported_versions
from codemigrate.llm import available_providers
from codemigrate.retrieval import RETRIEVER_NAMES

router = APIRouter(prefix="/api")
MAX_ZIP_BYTES = 20 * 1024 * 1024
RESULTS = REPO_ROOT / "results"


# ----------------------------------------------------------------------------- auth

@router.post("/auth/register", response_model=UserOut, status_code=201)
def register(body: RegisterIn, session: Session = Depends(get_session)) -> UserOut:
    email = body.email.lower()
    if session.exec(select(User).where(User.email == email)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    user = User(email=email, hashed_password=hash_password(body.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return UserOut(id=user.id, email=user.email)


@router.post("/auth/token", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(),
          session: Session = Depends(get_session)) -> TokenOut:
    user = session.exec(select(User).where(User.email == form.username.lower())).first()
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "wrong email or password")
    return TokenOut(access_token=create_token(user.id))


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> UserOut:
    return UserOut(id=user.id, email=user.email)


# ----------------------------------------------------------------------------- meta

@router.get("/meta")
def meta() -> dict:
    return {"versions": supported_versions(), "providers": available_providers(),
            "retrievers": list(RETRIEVER_NAMES), "default": {"from": "4.0", "to": "5.1"}}


# ----------------------------------------------------------------------------- projects

def _own_project(pid: int, user: User, session: Session) -> Project:
    project = session.get(Project, pid)
    if project is None or project.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
    return project


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectIn, user: User = Depends(current_user),
                   session: Session = Depends(get_session)) -> Project:
    project = Project(owner_id=user.id, name=body.name)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(user: User = Depends(current_user), session: Session = Depends(get_session)):
    return session.exec(select(Project).where(Project.owner_id == user.id)
                        .order_by(Project.created_at.desc())).all()


# ----------------------------------------------------------------------------- scans

def _validate_options(from_v: str, to_v: str, provider: str, retriever: str) -> None:
    versions = supported_versions()
    if from_v not in versions + ["3.2"] or to_v not in versions:
        raise HTTPException(422, f"versions must be in {versions}")
    if tuple(map(int, from_v.split("."))) >= tuple(map(int, to_v.split("."))):
        raise HTTPException(422, "from version must be older than to version")
    if provider not in available_providers():
        raise HTTPException(422, f"provider {provider!r} unavailable; have {available_providers()}")
    if retriever not in RETRIEVER_NAMES:
        raise HTTPException(422, f"retriever must be one of {RETRIEVER_NAMES}")


def _create_scan(project: Project, user: User, sources: list[tuple[str, str]], from_v: str,
                 to_v: str, provider: str, retriever: str, source_name: str,
                 session: Session) -> Scan:
    scan = Scan(project_id=project.id, owner_id=user.id, from_version=from_v, to_version=to_v,
                provider=provider, retriever=retriever, source_name=source_name,
                sources_json=json.dumps(sources))
    session.add(scan)
    session.commit()
    session.refresh(scan)
    jobs.submit(scan.id)
    return scan


@router.post("/projects/{pid}/scans", response_model=ScanOut, status_code=202)
def create_scan(pid: int, body: ScanIn, user: User = Depends(current_user),
                session: Session = Depends(get_session)) -> Scan:
    project = _own_project(pid, user, session)
    _validate_options(body.from_version, body.to_version, body.provider, body.retriever)
    sources = [(f.path.replace("\\", "/").lstrip("/"), f.content) for f in body.files]
    name = sources[0][0] if len(sources) == 1 else f"{len(sources)} files"
    return _create_scan(project, user, sources, body.from_version, body.to_version,
                        body.provider, body.retriever, name, session)


@router.post("/projects/{pid}/scans/upload", response_model=ScanOut, status_code=202)
async def upload_scan(pid: int, file: UploadFile = File(...), from_version: str = Form("4.0"),
                      to_version: str = Form("5.1"), provider: str = Form("offline"),
                      retriever: str = Form("hybrid"), user: User = Depends(current_user),
                      session: Session = Depends(get_session)) -> Scan:
    project = _own_project(pid, user, session)
    _validate_options(from_version, to_version, provider, retriever)
    data = await file.read(MAX_ZIP_BYTES + 1)
    if len(data) > MAX_ZIP_BYTES:
        raise HTTPException(413, "zip larger than 20 MB")
    try:
        zipfile.ZipFile(io.BytesIO(data)).testzip()
    except zipfile.BadZipFile as exc:
        raise HTTPException(422, "not a valid zip file") from exc
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "upload.zip"
        path.write_bytes(data)
        sources = list(iter_sources(path))
    if not sources:
        raise HTTPException(422, "zip contains no .py or template files")
    return _create_scan(project, user, sources, from_version, to_version, provider, retriever,
                        file.filename or "upload.zip", session)


@router.get("/projects/{pid}/scans", response_model=list[ScanOut])
def list_scans(pid: int, user: User = Depends(current_user),
               session: Session = Depends(get_session)):
    _own_project(pid, user, session)
    return session.exec(select(Scan).where(Scan.project_id == pid)
                        .order_by(Scan.created_at.desc())).all()


@router.get("/scans", response_model=list[ScanOut])
def all_scans(user: User = Depends(current_user), session: Session = Depends(get_session)):
    return session.exec(select(Scan).where(Scan.owner_id == user.id)
                        .order_by(Scan.created_at.desc()).limit(100)).all()


def _own_scan(sid: int, user: User, session: Session) -> Scan:
    scan = session.get(Scan, sid)
    if scan is None or scan.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "scan not found")
    return scan


@router.get("/scans/{sid}", response_model=ScanDetail)
def get_scan(sid: int, user: User = Depends(current_user),
             session: Session = Depends(get_session)) -> ScanDetail:
    scan = _own_scan(sid, user, session)
    return ScanDetail(**scan.model_dump(exclude={"sources_json", "result_json"}),
                      result=json.loads(scan.result_json) if scan.result_json else None,
                      sources=[SourceFile(path=p, content=c)
                               for p, c in json.loads(scan.sources_json)])


def _completed(scan: Scan) -> dict:
    if scan.result_json is None:
        raise HTTPException(409, f"scan is {scan.status}")
    return json.loads(scan.result_json)


@router.get("/scans/{sid}/report.md", response_class=PlainTextResponse)
def report_md(sid: int, user: User = Depends(current_user),
              session: Session = Depends(get_session)) -> PlainTextResponse:
    scan = _own_scan(sid, user, session)
    return PlainTextResponse(to_markdown(scan, _completed(scan)), media_type="text/markdown",
                             headers={"Content-Disposition":
                                      f'attachment; filename="codemigrate-scan-{sid}.md"'})


@router.get("/scans/{sid}/report.pdf")
def report_pdf(sid: int, user: User = Depends(current_user),
               session: Session = Depends(get_session)) -> Response:
    scan = _own_scan(sid, user, session)
    return Response(to_pdf(scan, _completed(scan)), media_type="application/pdf",
                    headers={"Content-Disposition":
                             f'attachment; filename="codemigrate-scan-{sid}.pdf"'})


# ----------------------------------------------------------------------------- results

@router.get("/results")
def results(split: str = "test") -> dict:
    """Benchmark tables and figure list generated by `make results` (empty if not run)."""
    out: dict = {"split": split, "comparison": [], "ablations": [], "figures": [], "meta": None}
    comp = RESULTS / "tables" / f"comparison_{split}.csv"
    if comp.exists():
        out["comparison"] = pd.read_csv(comp).fillna("n/a").to_dict(orient="records")
    abl = RESULTS / "tables" / f"ablations_{split}.csv"
    if abl.exists():
        out["ablations"] = pd.read_csv(abl).fillna("n/a").to_dict(orient="records")
    figs = RESULTS / "figures"
    if figs.exists():
        out["figures"] = sorted(p.name for p in figs.glob(f"*_{split}.png"))
    meta_path = RESULTS / f"run_meta_{split}.json"
    if meta_path.exists():
        out["meta"] = json.loads(meta_path.read_text())
    return out
