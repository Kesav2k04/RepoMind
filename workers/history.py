"""Evidence-first Git history analysis for RepoMind."""

from __future__ import annotations

from repository import RepositorySnapshot
from schemas import AgentReport, Finding


def analyze(snapshot: RepositorySnapshot) -> AgentReport:
    """Summarize bounded commit, contributor, and churn evidence.

    The repository snapshot limits Git history to a shallow recent window, so
    all language here explicitly describes *observed* rather than lifetime
    history.  Churn counts refer to commits touching a path, not lines changed.
    """
    commit_subjects = [subject.strip() for subject in snapshot.commit_messages if subject.strip()]
    contributors = [name.strip() for name in snapshot.contributors if name.strip()]
    churn_files = [(path, count) for path, count in snapshot.churn_files if path and count > 0]
    churn_paths = [path for path, _ in churn_files]
    findings: list[Finding] = []

    if churn_files:
        top_paths = churn_files[:5]
        top_file_labels = ", ".join(f"{path} ({count})" for path, count in top_paths)
        highest_count = top_paths[0][1]
        severity = "medium" if highest_count >= 8 else "info"
        title = "High-churn paths identified" if severity == "medium" else "Recently touched paths identified"
        findings.append(
            Finding(
                id="history-churn-paths",
                category="change_churn",
                title=title,
                detail=(
                    "In the bounded recent Git history, these paths were touched most often by commits: "
                    f"{top_file_labels}. Counts represent commit touches, not line changes."
                ),
                severity=severity,
                files=[path for path, _ in top_paths],
                recommendation=(
                    "Treat these paths as change-sensitive: make focused edits and run relevant checks before merging."
                ),
            )
        )

    if contributors and churn_paths:
        findings.append(
            Finding(
                id="history-contributor-signal",
                category="contributor_signal",
                title="Recent contributor context is available",
                detail=(
                    f"The bounded recent Git history contains {len(contributors)} distinct contributor name(s): "
                    f"{', '.join(contributors[:8])}."
                ),
                severity="info",
                files=churn_paths[:5],
                recommendation="Consult recent owners or commit context when modifying change-sensitive paths.",
            )
        )

    if commit_subjects and churn_paths:
        findings.append(
            Finding(
                id="history-recent-commit-context",
                category="commit_context",
                title="Recent commit subjects provide implementation context",
                detail=(
                    f"RepoMind retained {len(commit_subjects)} recent commit subject(s); the latest observed subject is "
                    f"'{commit_subjects[0]}'."
                ),
                severity="info",
                files=churn_paths[:3],
                recommendation="Review the corresponding commits before changing the most recently active areas.",
            )
        )

    summary = _summary(commit_subjects, contributors, churn_files)
    evidence_count = len(commit_subjects) + len(contributors) + len(churn_files)
    return AgentReport(
        role="history",
        label="History Archaeologist",
        summary=summary,
        findings=findings,
        confidence=_confidence(commit_subjects, contributors, churn_files),
        evidence_count=evidence_count,
    )


def _summary(
    commit_subjects: list[str], contributors: list[str], churn_files: list[tuple[str, int]]
) -> str:
    if not commit_subjects and not contributors and not churn_files:
        return "No accessible recent Git history was available in the bounded repository snapshot."
    segments: list[str] = []
    if commit_subjects:
        segments.append(f"Observed {len(commit_subjects)} recent commit subject(s)")
    if contributors:
        segments.append(f"{len(contributors)} recent contributor name(s)")
    if churn_files:
        segments.append(f"{len(churn_files)} churn-ranked path(s)")
    return "; ".join(segments) + "."


def _confidence(
    commit_subjects: list[str], contributors: list[str], churn_files: list[tuple[str, int]]
) -> float:
    evidence_sets = int(bool(commit_subjects)) + int(bool(contributors)) + int(bool(churn_files))
    if not evidence_sets:
        return 0.25
    return min(0.95, 0.45 + evidence_sets * 0.16)
