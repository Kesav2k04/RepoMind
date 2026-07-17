"""Evidence-backed risk analysis for a checked-out repository."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import PurePosixPath
import re

from repository import RepositorySnapshot
from schemas import AgentReport, Finding


_DYNAMIC_CODE_PATTERNS = (
    re.compile(r"\b(?:eval|exec)\s*\(", re.IGNORECASE),
    re.compile(r"\bnew\s+Function\s*\(", re.IGNORECASE),

)
_TLS_PATTERNS = (
    re.compile(r"\bverify\s*=\s*False\b", re.IGNORECASE),
    re.compile(r"\bCERT_NONE\b"),
    re.compile(r"_create_unverified_context\s*\("),
    re.compile(r"\bcheck_hostname\s*=\s*False\b", re.IGNORECASE),
    re.compile(r"\brejectUnauthorized\s*:\s*false\b", re.IGNORECASE),
    re.compile(r"(?:\bcurl\b[^\n]*\s(?:-k|--insecure)\b)"),
)
_PICKLE_PATTERNS = (
    re.compile(r"\bpickle\.(?:load|loads)\s*\("),
    re.compile(r"\b(?:dill|cloudpickle)\.(?:load|loads)\s*\("),
    re.compile(r"\bjoblib\.load\s*\("),
)
_MAINTENANCE_MARKER = re.compile(r"\b(?:TODO|FIXME|HACK|XXX)\b")
_ENV_REFERENCE = re.compile(
    r"\b(?:os\.getenv|os\.environ(?:\[|\.get)|process\.env|import\.meta\.env|"
    r"getenv\s*\(|ENV(?:\[|\.fetch)|System\.getenv)"
)

_NODE_MANIFESTS = {"package.json"}
_NODE_LOCKFILES = {
    "package-lock.json",
    "npm-shrinkwrap.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "bun.lock",
    "bun.lockb",
}
_PYTHON_MANIFESTS = {"pyproject.toml", "setup.py", "setup.cfg", "pipfile", "requirements.txt"}
_PYTHON_LOCKFILES = {"poetry.lock", "uv.lock", "pdm.lock", "pipfile.lock", "requirements.lock"}
_ENV_TEMPLATES = {".env.example", ".env.sample", ".env.template", "env.example"}


def analyze(snapshot: RepositorySnapshot) -> AgentReport:
    """Inspect bounded repository evidence for concrete, reviewable risk signals.

    This function intentionally reports potentially unsafe constructs rather than
    asserting exploitability. Every finding includes source or manifest paths from
    the supplied ``RepositorySnapshot``.
    """
    contents = _contents_by_path(snapshot)
    findings: list[Finding] = []

    dynamic_files = _matching_paths(contents, _DYNAMIC_CODE_PATTERNS)
    if dynamic_files:
        findings.append(
            Finding(
                id="risk-dynamic-code-execution",
                category="unsafe_dynamic_code",
                title="Potential dynamic code execution detected",
                detail=(
                    "Repository excerpts contain eval, exec, or Function-constructor usage. "
                    "Review each call to ensure no untrusted input can reach it."
                ),
                severity="high",
                files=dynamic_files,
                recommendation=(
                    "Replace dynamic evaluation with explicit parsing or a constrained allowlist; "
                    "validate any unavoidable input before execution."
                ),
            )
        )

    tls_files = _matching_paths(contents, _TLS_PATTERNS)
    if tls_files:
        findings.append(
            Finding(
                id="risk-tls-verification-disabled",
                category="transport_security",
                title="TLS certificate verification may be disabled",
                detail=(
                    "Repository excerpts contain an insecure TLS configuration pattern, such as "
                    "verify=False, CERT_NONE, rejectUnauthorized: false, or curl --insecure."
                ),
                severity="high",
                files=tls_files,
                recommendation=(
                    "Enable certificate and hostname verification in production; scope any local "
                    "development exception behind an explicit non-production configuration."
                ),
            )
        )

    pickle_files = _matching_paths(contents, _PICKLE_PATTERNS)
    if pickle_files:
        findings.append(
            Finding(
                id="risk-unsafe-deserialization",
                category="unsafe_deserialization",
                title="Pickle-style deserialization usage detected",
                detail=(
                    "Repository excerpts load pickle, dill, cloudpickle, or joblib data. These "
                    "formats can execute code when the serialized input is untrusted."
                ),
                severity="high",
                files=pickle_files,
                recommendation=(
                    "Only load artifacts from a trusted, integrity-checked source; prefer a data-only "
                    "format for inputs that can originate outside the trust boundary."
                ),
            )
        )

    marker_files = _matching_paths(contents, (_MAINTENANCE_MARKER,))
    if marker_files:
        findings.append(
            Finding(
                id="risk-maintenance-markers",
                category="maintenance",
                title="Unresolved maintenance markers detected",
                detail=(
                    "Repository excerpts contain TODO, FIXME, HACK, or XXX markers. These are "
                    "maintenance signals, not confirmed defects."
                ),
                severity="low",
                files=marker_files,
                recommendation="Triage the markers, link actionable items to tracked work, and remove obsolete notes.",
            )
        )

    lockfile_finding = _missing_lockfile_finding(snapshot)
    if lockfile_finding:
        findings.append(lockfile_finding)

    environment_finding = _missing_environment_template_finding(snapshot, contents)
    if environment_finding:
        findings.append(environment_finding)

    evidence_paths = {path for finding in findings for path in finding.files}
    summary = _summary(findings)
    return AgentReport(
        role="risk",
        label="Risk Auditor",
        summary=summary,
        findings=findings,
        confidence=0.9 if findings else 0.78,
        evidence_count=len(evidence_paths),
    )


def _contents_by_path(snapshot: RepositorySnapshot) -> dict[str, str]:
    """Merge bounded excerpts, preferring the longer important-file excerpt."""
    contents = dict(snapshot.sampled_contents)
    for path, content in snapshot.important_file_contents.items():
        if len(content) > len(contents.get(path, "")):
            contents[path] = content
    return contents


def _matching_paths(contents: dict[str, str], patterns: Iterable[re.Pattern[str]]) -> list[str]:
    return [
        path
        for path, content in sorted(contents.items())
        if any(pattern.search(content) for pattern in patterns)
    ][:8]


def _missing_lockfile_finding(snapshot: RepositorySnapshot) -> Finding | None:
    names = {PurePosixPath(path).name.lower() for path in snapshot.files}
    node_manifests = sorted(name for name in names if name in _NODE_MANIFESTS)
    python_manifests = sorted(name for name in names if name in _PYTHON_MANIFESTS)
    go_manifest = "go.mod" in names
    cargo_manifest = "cargo.toml" in names
    gem_manifest = "gemfile" in names

    missing: list[str] = []
    evidence: list[str] = []
    if node_manifests and not names.intersection(_NODE_LOCKFILES):
        missing.append("Node.js")
        evidence.extend(_files_named(snapshot.files, node_manifests))
    if python_manifests and not _has_python_lock(snapshot, names):
        missing.append("Python")
        evidence.extend(_files_named(snapshot.files, python_manifests))
    if go_manifest and "go.sum" not in names:
        missing.append("Go")
        evidence.extend(_files_named(snapshot.files, ["go.mod"]))
    if cargo_manifest and "cargo.lock" not in names:
        missing.append("Rust")
        evidence.extend(_files_named(snapshot.files, ["cargo.toml"]))
    if gem_manifest and "gemfile.lock" not in names:
        missing.append("Ruby")
        evidence.extend(_files_named(snapshot.files, ["gemfile"]))

    if not missing:
        return None
    ecosystems = ", ".join(missing)
    return Finding(
        id="risk-missing-dependency-lockfile",
        category="dependency_reproducibility",
        title="Dependency metadata lacks a recognized lockfile",
        detail=(
            f"{ecosystems} dependency metadata was found without its usual lockfile or an "
            "equivalent pinned requirements file in the repository inventory."
        ),
        severity="medium",
        files=sorted(set(evidence))[:8],
        recommendation=(
            "Commit the ecosystem's lockfile (or fully pinned requirements file) and keep it "
            "synchronized in dependency update workflows."
        ),
    )


def _has_python_lock(snapshot: RepositorySnapshot, names: set[str]) -> bool:
    if names.intersection(_PYTHON_LOCKFILES):
        return True
    requirement_paths = [
        path for path in snapshot.files if PurePosixPath(path).name.lower().startswith("requirements")
        and PurePosixPath(path).name.lower().endswith(".txt")
    ]
    if not requirement_paths:
        return False
    contents = _contents_by_path(snapshot)
    return any(_requirements_are_pinned(contents.get(path, "")) for path in requirement_paths)


def _requirements_are_pinned(content: str) -> bool:
    dependency_lines = [
        line.strip() for line in content.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", "-", "."))
    ]
    return bool(dependency_lines) and all("==" in line for line in dependency_lines)


def _missing_environment_template_finding(
    snapshot: RepositorySnapshot, contents: dict[str, str]
) -> Finding | None:
    names = {PurePosixPath(path).name.lower() for path in snapshot.files}
    if names.intersection(_ENV_TEMPLATES):
        return None
    evidence = _matching_paths(contents, (_ENV_REFERENCE,))
    if not evidence:
        return None
    return Finding(
        id="risk-missing-environment-template",
        category="configuration",
        title="Environment-variable usage has no checked-in template",
        detail=(
            "Repository excerpts reference environment variables, but the file inventory does not "
            "include a conventional .env example/template file."
        ),
        severity="low",
        files=evidence,
        recommendation=(
            "Add a secret-free .env.example documenting required variables, safe placeholders, "
            "and local-development defaults."
        ),
    )


def _files_named(paths: list[str], names: Iterable[str]) -> list[str]:
    name_set = set(names)
    return [path for path in paths if PurePosixPath(path).name.lower() in name_set]


def _summary(findings: list[Finding]) -> str:
    if not findings:
        return "No configured risk signals were found in the bounded repository evidence."
    high_count = sum(finding.severity == "high" for finding in findings)
    if high_count:
        return (
            f"Found {len(findings)} evidence-backed risk signals, including {high_count} high-severity "
            "pattern(s) requiring review."
        )
    return f"Found {len(findings)} evidence-backed maintenance or reproducibility risk signal(s)."
