"""Evidence-backed architecture inventory for RepoMind.

The architecture worker intentionally reports observable repository signals rather
than attempting to infer an entire design from a bounded checkout.  This keeps
the deterministic fallback useful and gives the reconciliation agent stable,
path-linked evidence to work from.
"""

from __future__ import annotations

from collections import Counter
from pathlib import PurePosixPath
import re

from repository import RepositorySnapshot
from schemas import AgentReport, Finding
from workers._shared import (
    WorkerObserver,
    bounded_confidence,
    contents_by_path,
    evidence_paths,
    file_evidence,
    notify,
    pattern_evidence,
)


_ENTRY_POINT_NAMES = {
    "__main__.py",
    "app.py",
    "asgi.py",
    "index.js",
    "index.jsx",
    "index.ts",
    "index.tsx",
    "main.go",
    "main.py",
    "main.rs",
    "main.js",
    "main.jsx",
    "main.ts",
    "main.tsx",
    "manage.py",
    "server.js",
    "server.ts",
    "wsgi.py",
}

# A signal is reported only when its well-known dependency/import token is
# present in a captured configuration or source excerpt.  This avoids making
# framework claims based on filenames alone.
_FRAMEWORK_SIGNALS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("FastAPI", ("fastapi",)),
    ("Django", ("django",)),
    ("Flask", ("flask",)),
    ("React", ("react",)),
    ("Next.js", ("next",)),
    ("Vue", ("vue",)),
    ("Svelte", ("svelte",)),
    ("Angular", ("@angular/core",)),
    ("Express", ("express",)),
    ("NestJS", ("@nestjs",)),
    ("Vite", ("vite",)),
    ("Ruby on Rails", ("rails",)),
    ("Laravel", ("laravel",)),
    ("Gin", ("github.com/gin-gonic/gin",)),
    ("Fiber", ("github.com/gofiber/fiber",)),
    ("Axum", ("axum",)),
    ("Actix Web", ("actix-web",)),
)

_SOURCE_ROOT_NAMES = {"app", "apps", "cmd", "lib", "packages", "server", "src"}


def analyze(snapshot: RepositorySnapshot, observer: WorkerObserver | None = None) -> AgentReport:
    """Summarize observable architectural evidence from a repository snapshot."""
    findings: list[Finding] = []

    notify(
        observer,
        "Reading file inventory and detecting language/framework signals",
        1,
        4,
        files_indexed=snapshot.file_count,
        manifests_found=len(snapshot.config_files),
    )
    language_finding = _language_finding(snapshot)
    if language_finding is not None:
        findings.append(language_finding)

    framework_finding = _framework_finding(snapshot)
    if framework_finding is not None:
        findings.append(framework_finding)

    notify(observer, "Finding conventional runtime entry points", 2, 4, files_indexed=snapshot.file_count)
    entry_point_finding = _entry_point_finding(snapshot)
    if entry_point_finding is not None:
        findings.append(entry_point_finding)

    notify(observer, "Mapping top-level module boundaries", 3, 4, files_indexed=snapshot.file_count)
    boundary_finding = _boundary_finding(snapshot)
    if boundary_finding is not None:
        findings.append(boundary_finding)

    notify(observer, "Reviewing build and repository configuration", 4, 4, manifests_found=len(snapshot.config_files))
    config_finding = _configuration_finding(snapshot)
    if config_finding is not None:
        findings.append(config_finding)

    summary = _summary(snapshot, findings)
    finding_paths = {path for finding in findings for path in finding.files}
    return AgentReport(
        role="architecture",
        label="Architecture Mapper",
        summary=summary,
        findings=findings,
        confidence=_confidence(snapshot, findings),
        evidence_count=len(finding_paths),
    )


def _language_finding(snapshot: RepositorySnapshot) -> Finding | None:
    counts = [(language, count) for language, count in snapshot.language_counts.most_common(5) if count]
    if not counts:
        return None
    detail = ", ".join(f"{language} ({count} file{'s' if count != 1 else ''})" for language, count in counts)
    evidence = [snapshot.language_examples[language] for language, _ in counts if language in snapshot.language_examples]
    locations = file_evidence(evidence, "Representative source file for the observed language profile.")
    return Finding(
        id="architecture-language-profile",
        category="languages",
        title="Language profile from the file inventory",
        detail=f"Observed language files: {detail}.",
        severity="info",
        files=evidence_paths(locations),
        confidence=bounded_confidence(0.96),
        evidence=locations,
        recommendation="Use the dominant language and its repository-local tooling when planning changes.",
    )


def _framework_finding(snapshot: RepositorySnapshot) -> Finding | None:
    content_by_path = contents_by_path(snapshot)
    matches: list[tuple[str, str]] = []
    for label, tokens in _FRAMEWORK_SIGNALS:
        source_paths = [
            path
            for path, content in content_by_path.items()
            if _contains_dependency_signal(content, tokens)
        ]
        if source_paths:
            matches.append((label, sorted(source_paths)[0]))
    if not matches:
        return None
    unique_matches = matches[:6]
    signal_text = ", ".join(f"{label} ({path})" for label, path in unique_matches)
    patterns = tuple(
        re.compile(rf"(?<![a-z0-9_-]){re.escape(token)}(?![a-z0-9_-])", re.IGNORECASE)
        for label, tokens in _FRAMEWORK_SIGNALS
        if any(label == matched_label for matched_label, _ in unique_matches)
        for token in tokens
    )
    locations = pattern_evidence(
        content_by_path,
        patterns,
        "Matched a framework or build-tool dependency/import token.",
    )
    return Finding(
        id="architecture-framework-signals",
        category="frameworks",
        title="Framework or build-tool signals found in captured content",
        detail=f"Dependency or import tokens indicate: {signal_text}.",
        severity="info",
        files=evidence_paths(locations) or _unique_paths(path for _, path in unique_matches),
        confidence=bounded_confidence(0.93),
        evidence=locations,
        recommendation="Confirm framework conventions in the linked configuration before changing application boundaries.",
    )


def _entry_point_finding(snapshot: RepositorySnapshot) -> Finding | None:
    candidates = [path for path in snapshot.files if _is_entry_point_candidate(path)]
    if not candidates:
        return None
    selected = sorted(candidates, key=_entry_point_sort_key)[:8]
    locations = file_evidence(selected, "Matches a conventional application or executable entry-point name.")
    return Finding(
        id="architecture-entry-point-candidates",
        category="entry_points",
        title="Conventional entry-point candidates",
        detail=(
            "These paths match common application or executable entry-point conventions: "
            f"{', '.join(selected)}. Validate the invoked command before treating a candidate as the runtime entry point."
        ),
        severity="info",
        files=evidence_paths(locations),
        confidence=bounded_confidence(0.82),
        evidence=locations,
        recommendation="Trace startup commands from repository configuration before modifying initialization behavior.",
    )


def _boundary_finding(snapshot: RepositorySnapshot) -> Finding | None:
    boundaries: Counter[str] = Counter()
    examples: dict[str, str] = {}
    for path in snapshot.files:
        parts = PurePosixPath(path).parts
        if len(parts) < 2:
            continue
        boundary = parts[0]
        boundaries[boundary] += 1
        examples.setdefault(boundary, path)
    if not boundaries:
        return None
    ranked = sorted(boundaries.items(), key=lambda item: (-item[1], item[0].lower()))[:10]
    evidence = [examples[name] for name, _ in ranked]
    inventory = ", ".join(f"{name}/ ({count})" for name, count in ranked)
    locations = file_evidence(evidence, "Representative file inside the observed top-level directory boundary.")
    return Finding(
        id="architecture-top-level-boundaries",
        category="module_boundaries",
        title="Top-level repository boundaries",
        detail=(
            "Top-level directories in the bounded file inventory: "
            f"{inventory}. Counts represent captured files, not ownership or runtime dependencies."
        ),
        severity="info",
        files=evidence_paths(locations),
        confidence=bounded_confidence(0.9),
        evidence=locations,
        recommendation="Preserve these directory boundaries unless the linked startup and build configuration supports a broader refactor.",
    )


def _configuration_finding(snapshot: RepositorySnapshot) -> Finding | None:
    if not snapshot.config_files:
        return None
    selected = sorted(snapshot.config_files)[:10]
    source_roots = sorted(
        {
            PurePosixPath(path).parts[0]
            for path in snapshot.files
            if len(PurePosixPath(path).parts) > 1
            and PurePosixPath(path).parts[0].lower() in _SOURCE_ROOT_NAMES
        }
    )
    source_note = f" Source-root candidates: {', '.join(f'{root}/' for root in source_roots)}." if source_roots else ""
    locations = file_evidence(selected, "Captured build or repository configuration file.")
    return Finding(
        id="architecture-configuration-inventory",
        category="configuration",
        title="Build and repository configuration inventory",
        detail=(
            "Captured configuration paths include: "
            f"{', '.join(selected)}.{source_note}"
        ),
        severity="info",
        files=evidence_paths(locations),
        confidence=bounded_confidence(0.91),
        evidence=locations,
        recommendation="Review the linked configuration files when choosing commands, entry points, or supported build workflows.",
    )


def _summary(snapshot: RepositorySnapshot, findings: list[Finding]) -> str:
    language = snapshot.primary_language
    if not findings:
        return (
            f"Architecture Mapper found no language, configuration, entry-point, or directory evidence "
            f"in the bounded inventory of {snapshot.file_count} files."
        )
    titles = ", ".join(finding.category.replace("_", " ") for finding in findings)
    return (
        f"Architecture Mapper inspected {snapshot.file_count} captured files; the primary observed language is "
        f"{language}. Evidence covers {titles}."
    )


def _confidence(snapshot: RepositorySnapshot, findings: list[Finding]) -> float:
    if not snapshot.files:
        return 0.35
    score = 0.55 + min(0.25, len(findings) * 0.05)
    if snapshot.important_file_contents or snapshot.config_files:
        score += 0.1
    if snapshot.language_counts:
        score += 0.05
    return min(score, 0.95)


def _contains_dependency_signal(content: str, tokens: tuple[str, ...]) -> bool:
    lower_content = content.lower()
    return any(re.search(rf"(?<![a-z0-9_-]){re.escape(token)}(?![a-z0-9_-])", lower_content) for token in tokens)


def _is_entry_point_candidate(path: str) -> bool:
    parsed = PurePosixPath(path)
    name = parsed.name.lower()
    if name in _ENTRY_POINT_NAMES:
        return True
    parts = parsed.parts
    return len(parts) == 2 and parts[0].lower() in _SOURCE_ROOT_NAMES and name in _ENTRY_POINT_NAMES


def _entry_point_sort_key(path: str) -> tuple[int, int, str]:
    parsed = PurePosixPath(path)
    name = parsed.name.lower()
    direct_root = 0 if len(parsed.parts) == 1 else 1
    preferred = 0 if name in {"main.py", "main.ts", "main.tsx", "main.js", "main.go", "main.rs"} else 1
    return (direct_root, preferred, path.lower())


def _unique_paths(paths: object) -> list[str]:
    return list(dict.fromkeys(path for path in paths if isinstance(path, str)))
