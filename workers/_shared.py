"""Small, evidence-safe helpers shared by RepoMind specialist workers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import re
from typing import Callable

from repository import RepositorySnapshot
from schemas import EvidenceLocation


@dataclass(frozen=True)
class WorkerUpdate:
    """One concrete activity emitted by a synchronous specialist worker."""

    action: str
    current: int
    total: int
    metrics: dict[str, int]


WorkerObserver = Callable[[WorkerUpdate], None]


def notify(
    observer: WorkerObserver | None,
    action: str,
    current: int,
    total: int,
    **metrics: int,
) -> None:
    """Publish best-effort worker telemetry without breaking the analysis."""
    if observer is None:
        return
    safe_metrics = {
        name: value
        for name, value in metrics.items()
        if isinstance(value, int) and value >= 0
    }
    try:
        observer(WorkerUpdate(action=action, current=current, total=total, metrics=safe_metrics))
    except Exception:
        # Progress is presentation metadata. A subscriber must never prevent a
        # deterministic, evidence-backed analysis from completing.
        return


def contents_by_path(snapshot: RepositorySnapshot) -> dict[str, str]:
    """Merge the repository helper's bounded excerpts, preferring longer copies."""
    contents: dict[str, str] = {}
    for source in (snapshot.sampled_contents, snapshot.important_file_contents):
        for path, content in source.items():
            if not isinstance(path, str) or not isinstance(content, str):
                continue
            if len(content) >= len(contents.get(path, "")):
                contents[path] = content
    return contents


def file_evidence(
    paths: Iterable[str],
    reason: str,
    *,
    limit: int = 8,
) -> list[EvidenceLocation]:
    """Create bounded file-level evidence when no precise line is available."""
    evidence: list[EvidenceLocation] = []
    for path in paths:
        if not isinstance(path, str) or not path or any(item.path == path for item in evidence):
            continue
        evidence.append(EvidenceLocation(path=path, reason=reason))
        if len(evidence) >= limit:
            break
    return evidence


def pattern_evidence(
    contents: Mapping[str, str],
    patterns: Iterable[re.Pattern[str]],
    reason: str,
    *,
    limit: int = 8,
) -> list[EvidenceLocation]:
    """Locate the first exact matching line per bounded source excerpt.

    RepositorySnapshot excerpts always begin at a source file's first byte, so
    line numbers calculated here are exact for any match that occurs within the
    captured excerpt. A file that was not captured never receives a fabricated
    source location.
    """
    compiled = tuple(patterns)
    evidence: list[EvidenceLocation] = []
    for path, content in sorted(contents.items()):
        if not isinstance(path, str) or not path or not isinstance(content, str):
            continue
        for line_number, line in enumerate(content.splitlines(), start=1):
            if not any(pattern.search(line) for pattern in compiled):
                continue
            excerpt = " ".join(line.strip().split())[:240]
            evidence.append(
                EvidenceLocation(
                    path=path,
                    line_start=line_number,
                    line_end=line_number,
                    excerpt=excerpt or None,
                    reason=reason,
                )
            )
            break
        if len(evidence) >= limit:
            break
    return evidence


def evidence_paths(evidence: Iterable[EvidenceLocation]) -> list[str]:
    """Return first-seen, non-empty paths for a finding's legacy ``files`` field."""
    return list(dict.fromkeys(item.path for item in evidence if item.path))


def bounded_confidence(value: float) -> float:
    """Keep worker confidence explicit and valid for the shared schema."""
    return max(0.0, min(1.0, round(value, 2)))
