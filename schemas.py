"""Pydantic contracts shared by the API, orchestration layer, and UI."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

AgentRole = Literal["architecture", "risk", "testing", "history"]
Severity = Literal["critical", "high", "medium", "low", "info"]
JobState = Literal["queued", "running", "completed", "failed"]


class AnalyzeRequest(BaseModel):
    """A public GitHub repository and optional change context to analyze."""

    repo_url: HttpUrl = Field(
        description="Public GitHub HTTPS repository URL, for example https://github.com/openai/openai-python"
    )
    task_description: str | None = Field(
        default=None,
        max_length=2_000,
        description="Optional description of the change the next coding agent is about to make.",
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
    confidence: float = Field(default=0.75, ge=0, le=1)
    evidence: list["EvidenceLocation"] = Field(default_factory=list)
    recommendation: str | None = None


class EvidenceLocation(BaseModel):
    """A concrete source location supporting a finding."""

    path: str
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    excerpt: str | None = None
    reason: str | None = None


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
    """Execution metadata without elevating hosted synthesis into canonical evidence."""

    mode: Literal["native_multi_agent", "evidence_fallback"]
    model: str | None = None
    root_agent: str = "/root"
    requested_subagents: int = 4
    completed_roles: list[AgentRole] = Field(default_factory=list)
    priority_finding_ids: list[str] = Field(default_factory=list)
    model_tool_calls: int = 0
    firewall_proposed_claims: int = 0
    firewall_verified_claims: int = 0
    duration_ms: int = 0
    note: str | None = None


class AnalysisMetrics(BaseModel):
    files_analyzed: int = 0
    sampled_files: int = 0
    manifests_found: int = 0
    tests_discovered: int = 0
    commits_inspected: int = 0
    findings_published: int = 0
    artifacts_generated: int = 2
    duration_ms: int = 0
    partial_analysis: bool = False
    discovered_files: int = 0
    skipped_files: int = 0
    content_truncated: bool = False
    model_tool_calls: int = 0
    model_workers_completed: int = 0


class AnalysisScope(BaseModel):
    """Explicit boundaries for a bounded repository analysis."""

    status: Literal["complete", "partial"] = "complete"
    discovered_files: int = 0
    selected_files: int = 0
    files_excluded_by_selection: int = 0
    reasons: list[str] = Field(default_factory=list)


class ArtifactValidation(BaseModel):
    """What was mechanically checked before artifacts were presented."""

    artifacts_validated: bool = False
    proposed_claims: int = 0
    validated_findings: int = 0
    rejected_claims: int = 0
    message: str | None = None


class TaskBrief(BaseModel):
    """Evidence-derived handoff focused on an optional user-supplied change."""

    task_description: str
    priority_finding_ids: list[str] = Field(default_factory=list)
    review_paths: list[str] = Field(default_factory=list)
    verification_commands: list[str] = Field(default_factory=list)


class ReconciliationDecision(BaseModel):
    disposition: Literal["accepted", "merged", "deferred"]
    finding_ids: list[str] = Field(default_factory=list)
    rationale: str


class ReconciliationSummary(BaseModel):
    accepted_count: int = 0
    merged_count: int = 0
    deferred_count: int = 0
    decisions: list[ReconciliationDecision] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    repository: RepositoryInfo
    reports: list[AgentReport]
    agents_md: str
    repo_map: RepositoryMap
    orchestration: OrchestrationMeta
    metrics: AnalysisMetrics = Field(default_factory=AnalysisMetrics)
    reconciliation: ReconciliationSummary = Field(default_factory=ReconciliationSummary)
    analysis_scope: AnalysisScope = Field(default_factory=AnalysisScope)
    validation: ArtifactValidation = Field(default_factory=ArtifactValidation)
    task_brief: TaskBrief | None = None


class ProgressEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    phase: str
    message: str
    role: AgentRole | None = None
    action: str | None = None
    current: int | None = Field(default=None, ge=0)
    total: int | None = Field(default=None, ge=0)
    percent: int | None = Field(default=None, ge=0, le=100)
    metrics: dict[str, int] = Field(default_factory=dict)


class AnalysisStatus(BaseModel):
    job_id: str
    status: JobState
    repository_url: str
    task_description: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    events: list[ProgressEvent] = Field(default_factory=list)
    result: AnalysisResult | None = None
    error: str | None = None
