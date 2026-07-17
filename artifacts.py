"""Deterministic, evidence-backed RepoMind artifacts."""

from __future__ import annotations

from pathlib import PurePosixPath

from repository import RepositorySnapshot
from schemas import AgentReport, ArtifactValidation, Finding, RepoNode, RepositoryMap

_RISK_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
_RISK_LEGEND = {
    "critical": "Immediate security or correctness concern",
    "high": "Review before changing or releasing",
    "medium": "Change-sensitive or incomplete coverage signal",
    "low": "Maintainability or onboarding concern",
    "info": "Structural repository context",
}


def generate_agents_md(snapshot: RepositorySnapshot, reports: list[AgentReport]) -> str:
    """Create practical, evidence-first instructions for a future coding agent."""
    report_by_role = {report.role: report for report in reports}
    architecture = report_by_role["architecture"]
    risk = report_by_role["risk"]
    testing = report_by_role["testing"]
    history = report_by_role["history"]
    entry_points = _finding_files(architecture, "architecture-entry-point-candidates")
    material_risks = [
        finding for finding in risk.findings if finding.severity in {"critical", "high", "medium"}
    ]
    churn_paths = _finding_files(history, "history-churn-paths")
    important_files = _unique_paths(
        entry_points + snapshot.config_files + [path for finding in material_risks for path in finding.files]
    )

    lines = [
        "# AGENTS.md",
        "",
        "## Overview",
        "",
        f"- **Repository:** {snapshot.name}",
        f"- **Primary observed language:** {snapshot.primary_language}",
        f"- **Bounded analysis inventory:** {snapshot.file_count} files",
        f"- **Architecture signal:** {architecture.summary}",
        "",
        "## Architecture",
        "",
        "- Read the nearest `AGENTS.md`, `README`, and relevant manifest before editing.",
        "- Keep changes within the smallest relevant module boundary; trace call sites before altering behavior.",
    ]
    if entry_points:
        lines.append(
            "- Verify likely entry points before editing startup behavior: "
            + ", ".join(f"`{path}`" for path in entry_points[:8])
            + "."
        )
    if snapshot.config_files:
        lines.append(
            "- Key manifests/configuration: "
            + ", ".join(f"`{path}`" for path in snapshot.config_files[:10])
            + "."
        )
    if snapshot.partial_analysis:
        lines.append(
            "- **Analysis scope:** Partial. RepoMind retained bounded evidence only; "
            "treat unscanned or truncated files as unknown rather than safe."
        )

    lines += ["", "## Important Files", ""]
    if important_files:
        lines.extend(f"- `{path}` - {_purpose(path)}." for path in important_files[:12])
    else:
        lines.append(
            "- No entry-point or manifest file could be confirmed from bounded evidence; inspect repository documentation first."
        )

    lines += ["", "## Risk Areas", ""]
    if material_risks:
        lines.extend(_finding_line(finding) for finding in material_risks[:8])
    else:
        lines.append(
            "- No medium-or-higher deterministic risk signal was detected; still review trust boundaries before changing them."
        )

    lines += ["", "## Testing Strategy", ""]
    if snapshot.test_commands:
        lines.extend(f"- Run `{command}` when it applies to the changed area." for command in snapshot.test_commands)
    else:
        lines.append("- Inspect repository documentation and manifests to select a focused verification command before merging.")
    for finding in testing.findings:
        if finding.severity in {"medium", "high", "critical"}:
            lines.append(f"- Address: {finding.title} - {finding.detail}")

    lines += ["", "## Things Not to Touch", ""]
    protected = [finding for finding in material_risks if finding.severity in {"critical", "high"}]
    if protected:
        for finding in protected[:5]:
            paths = ", ".join(f"`{path}`" for path in finding.files[:4]) or "the linked code path"
            lines.append(f"- Avoid changing {paths} casually: {_short_reason(finding)}")
    elif churn_paths:
        lines.append(
            "- Do not broaden changes in recent high-churn paths without reviewing nearby commits: "
            + ", ".join(f"`{path}`" for path in churn_paths[:8])
            + "."
        )
    else:
        lines.append(
            "- No protected path was detected. Treat authentication, deployment, and dependency changes as review-required until local context proves otherwise."
        )

    lines += ["", "## Coding Conventions", ""]
    lines += [
        "- Make focused diffs; do not mix formatting-only rewrites with behavioral changes.",
        "- Do not commit secrets, `.env` files, dependency directories, or generated build output.",
        "- Update tests and documentation whenever public behavior or configuration changes.",
        "- Preserve repository-local formatting and test tooling rather than introducing a parallel stack.",
    ]

    lines += ["", "## Verification Checklist", ""]
    lines += [
        "- [ ] Re-read the closest entry point, manifest, and call sites affected by the change.",
        "- [ ] Run the focused repository test command or explain why one is unavailable.",
        "- [ ] Check changed configuration for secret exposure and dependency reproducibility.",
        "- [ ] Update relevant tests and documentation, then inspect the final diff for unrelated changes.",
    ]

    lines += ["", "## Change-Sensitive Context", ""]
    if churn_paths:
        lines.append(
            "- Recent high-churn paths: "
            + ", ".join(f"`{path}`" for path in churn_paths[:8])
            + ". Review nearby history before changing them."
        )
    else:
        lines.append("- Recent Git-history signals were limited; inspect local context and nearby commits before broad changes.")
    return "\n".join(lines).strip() + "\n"


def build_repository_map(snapshot: RepositorySnapshot, reports: list[AgentReport]) -> RepositoryMap:
    """Build a compact, structured map whose risk labels come from real findings."""
    risk_by_path = _risk_by_path(reports)
    root_nodes: list[RepoNode] = []
    directories = sorted(
        {PurePosixPath(path).parts[0] for path in snapshot.files if len(PurePosixPath(path).parts) > 1}
    )
    for directory in directories[:16]:
        children_paths = [path for path in snapshot.files if path.startswith(f"{directory}/")][:10]
        child_nodes = [
            RepoNode(path=path, kind="file", purpose=_purpose(path), risk=risk_by_path.get(path, "info"))
            for path in children_paths
        ]
        directory_risk = max(
            (child.risk for child in child_nodes),
            key=lambda value: _RISK_ORDER[value],
            default="info",
        )
        root_nodes.append(
            RepoNode(
                path=f"{directory}/",
                kind="directory",
                purpose="Top-level repository boundary.",
                risk=directory_risk,
                children=child_nodes,
            )
        )
    root_nodes.extend(
        RepoNode(path=path, kind="file", purpose=_purpose(path), risk=risk_by_path.get(path, "info"))
        for path in snapshot.files
        if len(PurePosixPath(path).parts) == 1
    )
    markdown_lines = [f"# {snapshot.name} - risk-annotated repository map", ""]
    for node in root_nodes:
        markdown_lines.append(f"- [{node.risk.upper()}] `{node.path}` - {node.purpose}")
        markdown_lines.extend(
            f"  - [{child.risk.upper()}] `{child.path}` - {child.purpose}" for child in node.children
        )
    scope = " Partial analysis: review the analysis scope before assuming unscanned files are safe." if snapshot.partial_analysis else ""
    return RepositoryMap(
        overview=(
            f"{snapshot.file_count} bounded-inventory files; primary observed language: "
            f"{snapshot.primary_language}.{scope}"
        ),
        nodes=root_nodes,
        risk_legend=_RISK_LEGEND,
        markdown="\n".join(markdown_lines) + "\n",
    )


def _risk_by_path(reports: list[AgentReport]) -> dict[str, str]:
    result: dict[str, str] = {}
    for report in reports:
        for finding in report.findings:
            for path in finding.files:
                current = result.get(path, "info")
                if _RISK_ORDER[finding.severity] > _RISK_ORDER[current]:
                    result[path] = finding.severity
    return result


def _finding_files(report: AgentReport, identifier: str) -> list[str]:
    return [path for finding in report.findings if finding.id == identifier for path in finding.files]


def _finding_line(finding: Finding) -> str:
    """Render a compact, source-linked risk finding without inventing evidence."""
    evidence = finding.evidence[0] if finding.evidence else None
    if evidence is not None:
        location = f"`{evidence.path}`"
        if evidence.line_start is not None:
            location += f":{evidence.line_start}"
        reason = evidence.reason or finding.detail
    else:
        location = ", ".join(f"`{path}`" for path in finding.files[:3]) or "repository inventory"
        reason = finding.detail
    return (
        f"- **{finding.severity.upper()} | {finding.confidence:.0%} confidence - {finding.title}:** "
        f"Evidence: {location}. Reason: {_short_text(reason)}"
    )


def _short_reason(finding: Finding) -> str:
    evidence = finding.evidence[0] if finding.evidence else None
    return _short_text((evidence.reason if evidence else None) or finding.detail)


def _short_text(value: str, limit: int = 220) -> str:
    normalized = " ".join((value or "").split())
    return normalized if len(normalized) <= limit else normalized[: limit - 1].rstrip() + "..."


def _unique_paths(paths: list[str]) -> list[str]:
    return list(dict.fromkeys(path for path in paths if isinstance(path, str) and path))


def _purpose(path: str) -> str:
    name = PurePosixPath(path).name.lower()
    if name in {"readme.md", "agents.md"}:
        return "Developer guidance and documentation"
    if "test" in name or "/tests/" in f"/{path.lower()}":
        return "Test coverage"
    if name in {"package.json", "pyproject.toml", "requirements.txt", "go.mod", "cargo.toml"}:
        return "Dependency or build manifest"
    if name.startswith(("main.", "app.", "server.", "index.")):
        return "Likely application entry point"
    return "Repository source or configuration"


def validate_generated_artifacts(
    snapshot: RepositorySnapshot,
    reports: list[AgentReport],
    agents_md: str,
    repository_map: RepositoryMap,
) -> ArtifactValidation:
    """Mechanically verify canonical artifacts before they are returned to a user.

    Artifacts are deterministic and this check prevents later changes from
    presenting ungrounded paths or a malformed agent guide as trusted output.
    """
    required_sections = (
        "## Overview",
        "## Architecture",
        "## Important Files",
        "## Risk Areas",
        "## Testing Strategy",
        "## Things Not to Touch",
        "## Coding Conventions",
        "## Verification Checklist",
    )
    if not isinstance(agents_md, str) or any(section not in agents_md for section in required_sections):
        raise ValueError("Generated AGENTS.md did not pass the required-section validation.")
    if not isinstance(repository_map.markdown, str) or not repository_map.markdown.strip():
        raise ValueError("Generated repository map did not pass the content validation.")

    known_files = set(snapshot.files)
    known_directories = {f"{PurePosixPath(path).parts[0]}/" for path in snapshot.files if len(PurePosixPath(path).parts) > 1}
    nodes = [node for root in repository_map.nodes for node in _walk_map_nodes(root)]
    invalid_paths = [
        node.path
        for node in nodes
        if (node.kind == "file" and node.path not in known_files)
        or (node.kind == "directory" and node.path not in known_directories)
    ]
    if invalid_paths:
        raise ValueError("Generated repository map referenced a path outside the bounded inventory.")

    findings = [finding for report in reports for finding in report.findings]
    missing_evidence = [finding.id for finding in findings if not finding.evidence]
    if missing_evidence:
        raise ValueError("A generated artifact would include finding(s) without evidence.")
    return ArtifactValidation(
        artifacts_validated=True,
        validated_findings=len(findings),
        rejected_claims=0,
        message="Canonical artifacts were generated and checked against deterministic evidence.",
    )


def _walk_map_nodes(node: RepoNode) -> list[RepoNode]:
    """Flatten a generated map for path-boundary validation."""
    return [node, *(child for descendant in node.children for child in _walk_map_nodes(descendant))]
