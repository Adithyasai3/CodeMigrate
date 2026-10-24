"""Shared data models passed between pipeline stages."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from codemigrate.kb.schema import KBEntry


class RefKind(StrEnum):
    IMPORT = "import"
    ATTRIBUTE = "attribute"
    CALL = "call"
    METHOD = "method"  # attribute on an unresolved receiver, e.g. self.assertFormsetError
    SETTING = "setting"
    STRING = "string"  # dotted path in a string literal (INSTALLED_APPS, MIDDLEWARE, ...)
    META = "model_meta"
    MODULE_VAR = "module_variable"
    TEMPLATE = "template"


class CodeRef(BaseModel):
    """One reference to a (possibly) library API in user code, with exact location."""

    file: str
    line: int
    col: int
    end_col: int | None = None
    symbol: str
    raw_text: str
    kind: RefKind
    context: str = ""
    call_args: int | None = None  # positional argument count when the ref is called
    call_kwargs: list[str] = Field(default_factory=list)


class ScannedFile(BaseModel):
    path: str
    refs: list[CodeRef] = Field(default_factory=list)
    error: str | None = None
    source: str | None = None


class ScoredEntry(BaseModel):
    entry: KBEntry
    score: float
    retriever: str


class Evidence(BaseModel):
    """Retrieved KB entries attached to one code reference."""

    ref: CodeRef
    entries: list[ScoredEntry]


class FindingStatus(StrEnum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"


class Finding(BaseModel):
    """A claim produced by a reasoner (LLM or rule) before validation."""

    file: str
    line: int
    symbol: str
    change_type: str = ""
    explanation: str = ""
    suggested_fix: str = ""
    cited_ids: list[str] = Field(default_factory=list)
    confidence: float = 1.0


class ValidatedFinding(Finding):
    status: FindingStatus
    reject_reason: str | None = None
    evidence: list[KBEntry] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    patch: str | None = None


class UpdatedFile(BaseModel):
    """A whole updated file: safe patches applied, optional verified LLM rewrite, TODO notes."""

    path: str
    content: str
    diff: str
    auto_fixed: list[int] = Field(default_factory=list)  # original line numbers
    llm_fixed: list[int] = Field(default_factory=list)
    manual: list[int] = Field(default_factory=list)  # left as TODO comments


class ScanResult(BaseModel):
    from_version: str
    to_version: str
    system: str
    findings: list[ValidatedFinding] = Field(default_factory=list)
    rejected: list[ValidatedFinding] = Field(default_factory=list)
    updated_files: list[UpdatedFile] = Field(default_factory=list)
    files_scanned: int = 0
    file_errors: dict[str, str] = Field(default_factory=dict)
    refs_found: int = 0
    llm_calls: int = 0
    cached_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    latency_s: float = 0.0
