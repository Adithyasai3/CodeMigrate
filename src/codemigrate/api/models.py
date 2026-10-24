"""Database tables (SQLModel) and API request/response schemas."""


from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel
from pydantic import Field as PField
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class ScanStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=utcnow)


class Project(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    name: str
    created_at: datetime = Field(default_factory=utcnow)


class Scan(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    status: ScanStatus = Field(default=ScanStatus.PENDING)
    from_version: str
    to_version: str
    provider: str = "offline"
    retriever: str = "hybrid"
    source_name: str = "pasted code"
    sources_json: str = "[]"  # [[path, text], ...] kept so the UI can highlight lines
    result_json: str | None = None
    error: str | None = None
    findings_count: int = 0
    created_at: datetime = Field(default_factory=utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None


# ----------------------------------------------------------------------------- API schemas

class RegisterIn(BaseModel):
    email: str = PField(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=254)
    password: str = PField(min_length=8, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str


class ProjectIn(BaseModel):
    name: str = PField(min_length=1, max_length=120)


class ProjectOut(BaseModel):
    id: int
    name: str
    created_at: datetime


class SourceFile(BaseModel):
    path: str = PField(min_length=1, max_length=300)
    content: str = PField(max_length=500_000)


class ScanIn(BaseModel):
    files: list[SourceFile] = PField(min_length=1, max_length=200)
    from_version: str = "4.0"
    to_version: str = "5.1"
    provider: str = "offline"
    retriever: str = "hybrid"


class ScanOut(BaseModel):
    id: int
    project_id: int
    status: ScanStatus
    from_version: str
    to_version: str
    provider: str
    retriever: str
    source_name: str
    findings_count: int
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ScanDetail(ScanOut):
    result: dict | None = None
    sources: list[SourceFile] = []
