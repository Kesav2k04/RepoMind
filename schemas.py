"""Pydantic contracts shared by the API, orchestration layer, and UI."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

AgentRole = Literal["architecture", "risk", "testing", "history"]
Severity = Literal["critical", "high", "medium", "low", "info"]
JobState = Literal["queued", "running", "completed", "failed"]


class AnalyzeRequest(BaseModel):
    """A public GitHub repository to analyze."""

    repo_url: HttpUrl = Field(
        description="Public GitHub HTTPS repository URL, for example https://github.com/openai/openai-python"
    )


class RepositoryInfo(BaseModel):
    name: str
    url: str
    default_branch: str | None = None
    commit: str | None = None
    file_count: int = 0
    primary_language: str = "Unknown"


class Finding(BaseModel):
    id: str
    category: str
    title: str
    detail: str
    severity: Severity = "info"
    files: list[str] = Field(default_factory=list)
    recommendation: str | None = None


class AgentReport(BaseModel):
    role: AgentRole
    label: str
    summary: str
    findings: list[Finding] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    evidence_count: int = 0


class RepoNode(BaseModel):
    path: str
    kind: Literal["directory", "file"]
    purpose: str
    risk: Severity = "info"
    children: list["RepoNode"] = Field(default_factory=list)


class RepositoryMap(BaseModel):
    overview: str
    nodes: list[RepoNode]
    risk_legend: dict[Severity, str]
    markdown: str


class OrchestrationMeta(BaseModel):
    mode: Literal["native_multi_agent", "evidence_fallback"]
    model: str | None = None
    root_agent: str = "/root"
    requested_subagents: int = 4
    completed_roles: list[AgentRole] = Field(default_factory=list)
    duration_ms: int = 0
    note: str | None = None


class AnalysisResult(BaseModel):
    repository: RepositoryInfo
    reports: list[AgentReport]
    agents_md: str
    repo_map: RepositoryMap
    orchestration: OrchestrationMeta


class ProgressEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    phase: str
    message: str
    role: AgentRole | None = None


class AnalysisStatus(BaseModel):
    job_id: str
    status: JobState
    repository_url: str
    created_at: datetime
    completed_at: datetime | None = None
    events: list[ProgressEvent] = Field(default_factory=list)
    result: AnalysisResult | None = None
    error: str | None = None
